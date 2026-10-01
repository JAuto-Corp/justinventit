#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = dirname(fileURLToPath(import.meta.url));
const DEFAULT_SCHEMA = resolve(HERE, '../docs/seat-record.schema.json');
const IMPLEMENTED = new Set([
    '$schema',
    '$id',
    'title',
    'description',
    '$defs',
    '$ref',
    'type',
    'enum',
    'const',
    'pattern',
    'required',
    'properties',
    'additionalProperties',
    'items',
    'uniqueItems',
    'minimum',
    'minLength',
    'maxLength',
    'format',
    'allOf',
    'if',
    'then',
    'else'
]);
const IMPLEMENTED_FORMATS = new Set([
    'date-time'
]);
export function isRfc3339(v) {
    if (typeof v !== 'string') return false;
    const m = /^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:[Zz]|([+-])(\d{2}):(\d{2}))$/.exec(v);
    if (!m) return false;
    const [, Y, MO, D, H, MI, S, sign, OH, OM] = m;
    const year = +Y, month = +MO, day = +D, hour = +H, minute = +MI, second = +S;
    if (month < 1 || month > 12) return false;
    if (hour > 23 || minute > 59) return false;
    if (OH !== undefined && (+OH > 23 || +OM > 59)) return false;
    if (second > 60) return false;
    const daysInMonth = (y, mo)=>{
        const isLeap = y % 4 === 0 && y % 100 !== 0 || y % 400 === 0;
        return [
            31,
            isLeap ? 29 : 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31
        ][mo - 1];
    };
    if (day < 1 || day > daysInMonth(year, month)) return false;
    if (second === 60) {
        const offMin = OH === undefined ? 0 : (sign === '-' ? -1 : 1) * (+OH * 60 + +OM);
        const total = hour * 60 + minute - offMin;
        const utcMinutes = (total % 1440 + 1440) % 1440;
        if (utcMinutes !== 23 * 60 + 59) return false;
        let uy = year, um = month, ud = day + Math.floor(total / 1440);
        while(ud > daysInMonth(uy, um)){
            ud -= daysInMonth(uy, um);
            if (++um > 12) {
                um = 1;
                uy++;
            }
        }
        while(ud < 1){
            if (--um < 1) {
                um = 12;
                uy--;
            }
            ud += daysInMonth(uy, um);
        }
        if (ud !== daysInMonth(uy, um)) return false;
    }
    return true;
}
const SHAPED = [
    [
        /^\/model$/,
        'type',
        (c)=>`model must be resolved in state=${String(c.root.state)} (§3 tier verification)`
    ],
    [
        /^\/effort$/,
        'type',
        (c)=>`effort must be resolved in state=${String(c.root.state)} (§3 tier verification)`
    ],
    [
        /^\/effort$/,
        'enum',
        (c)=>`effort must be resolved in state=${String(c.root.state)} and one of the matrix values (§3 tier verification)`
    ],
    [
        /^\/(lease|watcher)$/,
        'type',
        (c)=>`${c.name} must be an object (present-but-null is indistinguishable from absent)`
    ],
    [
        /^\/(lease|watcher|heartbeat|conclusion|last_probe)$/,
        'required',
        (c)=>`${c.name} requires ${c.detail}`
    ],
    [
        /^\/[a-z_]+(\/[^/]+)*$/,
        'additionalProperties',
        (c)=>`unknown key in ${c.name}: ${c.detail}`
    ],
    [
        /^\/(lease\/epoch|watcher\/generation|heartbeat\/wake_count|heartbeat\/cadence_seconds)$/,
        'minimum',
        (c)=>`${c.name} must be an integer >= ${c.detail}`
    ],
    [
        /^\/heartbeat\/cadence_seconds$/,
        'type',
        ()=>'heartbeat.cadence_seconds must be a bare integer — prose here is rejected, never coerced'
    ],
    [
        /^\/capabilities\/[^/]+\/value$/,
        'type',
        (c)=>`${c.name} must be a ${c.detail} ($defs/boolCapability where declared — a probe result is not free-form)`
    ],
    [
        /^\/capabilities\/[^/]+\/probed_at$/,
        'format',
        (c)=>`${c.name} must be an RFC 3339 timestamp — an unprobed capability is ABSENT, never assumed`
    ],
    [
        /^$/,
        'required',
        (c)=>`missing required key: ${c.detail}`
    ],
    [
        /^$/,
        'additionalProperties',
        (c)=>`unknown key: ${c.detail}`
    ],
    [
        /^\/state$/,
        'enum',
        ()=>'state must be one of booted|active|standby|dormant|parked — stalled/dead are derived verdicts, never self-written'
    ]
];
function humanName(path) {
    return path.replace(/^\//, '').replace(/\//g, '.') || 'the record';
}
function typeMatches(t, v) {
    switch(t){
        case 'null':
            return v === null;
        case 'string':
            return typeof v === 'string';
        case 'boolean':
            return typeof v === 'boolean';
        case 'number':
            return typeof v === 'number';
        case 'integer':
            return typeof v === 'number' && Number.isInteger(v);
        case 'array':
            return Array.isArray(v);
        case 'object':
            return v !== null && typeof v === 'object' && !Array.isArray(v);
        default:
            throw new Error(`unimplemented type: ${t}`);
    }
}
function describe(v) {
    if (v === null) return 'null';
    if (Array.isArray(v)) return 'array';
    return typeof v;
}
function deepEqual(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
}
class Validator {
    schema;
    root;
    errs = [];
    constructor(schema, root){
        this.schema = schema;
        this.root = root;
    }
    fail(path, keyword, detail, fallback) {
        const name = humanName(path);
        for (const [re, kw, shape] of SHAPED){
            if (kw === keyword && re.test(path)) {
                this.errs.push(shape({
                    name,
                    detail,
                    root: this.root
                }));
                return;
            }
        }
        this.errs.push(`${name}: ${fallback}`);
    }
    deref(s) {
        if (typeof s === 'object' && s !== null && typeof s.$ref === 'string') {
            const ref = s.$ref;
            if (!ref.startsWith('#/$defs/')) throw new Error(`unimplemented $ref target: ${ref}`);
            const target = this.schema.$defs?.[ref.slice('#/$defs/'.length)];
            if (!target) throw new Error(`unresolvable $ref: ${ref}`);
            return target;
        }
        return s;
    }
    matches(schema, data) {
        const probe = new Validator(this.schema, this.root);
        probe.check(schema, data, '');
        return probe.errors.length === 0;
    }
    check(schemaIn, data, path) {
        const schema = this.deref(schemaIn);
        if (schema === true || schema === undefined) return;
        if (schema === false) {
            this.fail(path, 'false', '', 'is not allowed here');
            return;
        }
        const s = schema;
        if (s.type !== undefined) {
            const types = Array.isArray(s.type) ? s.type : [
                s.type
            ];
            if (!types.some((t)=>typeMatches(t, data))) {
                this.fail(path, 'type', types.join('|'), `expected ${types.join(' or ')}, got ${describe(data)}`);
                return;
            }
        }
        if (s.const !== undefined && !deepEqual(s.const, data)) this.fail(path, 'const', String(s.const), `must be ${JSON.stringify(s.const)}`);
        if (Array.isArray(s.enum) && !s.enum.some((e)=>deepEqual(e, data))) this.fail(path, 'enum', s.enum.map((e)=>String(e)).join('|'), `must be one of ${s.enum.map((e)=>JSON.stringify(e)).join(', ')}`);
        if (typeof s.pattern === 'string' && typeof data === 'string' && !new RegExp(s.pattern).test(data)) this.fail(path, 'pattern', s.pattern, `must match ${s.pattern}`);
        if (typeof s.minimum === 'number' && typeof data === 'number' && data < s.minimum) this.fail(path, 'minimum', String(s.minimum), `must be >= ${s.minimum}`);
        const codePoints = typeof data === 'string' ? [
            ...data
        ].length : 0;
        if (typeof s.minLength === 'number' && typeof data === 'string' && codePoints < s.minLength) this.fail(path, 'minLength', String(s.minLength), `must be at least ${s.minLength} character(s) — an empty string is not a value`);
        if (typeof s.maxLength === 'number' && typeof data === 'string' && codePoints > s.maxLength) this.fail(path, 'maxLength', String(s.maxLength), `must be at most ${s.maxLength} characters`);
        if (s.format === 'date-time' && typeof data === 'string' && !isRfc3339(data)) this.fail(path, 'format', 'date-time', 'must be an RFC 3339 timestamp');
        if (Array.isArray(data)) {
            if (s.items !== undefined) data.forEach((v, i)=>this.check(s.items, v, `${path}/${i}`));
            if (s.uniqueItems === true && new Set(data.map((v)=>JSON.stringify(v))).size !== data.length) this.fail(path, 'uniqueItems', '', 'must have unique items');
        }
        if (data !== null && typeof data === 'object' && !Array.isArray(data)) {
            const o = data;
            const props = s.properties ?? {};
            if (Array.isArray(s.required)) {
                const req = s.required;
                const missing = req.filter((k)=>!(k in o));
                if (missing.length) {
                    if (path === '') for (const k of missing)this.fail(path, 'required', k, `missing required key: ${k}`);
                    else this.fail(path, 'required', req.join(', '), `requires ${req.join(', ')} (missing: ${missing.join(', ')})`);
                }
            }
            for (const [k, v] of Object.entries(o)){
                if (Object.hasOwn(props, k)) {
                    this.check(props[k], v, `${path}/${k}`);
                    continue;
                }
                if (s.additionalProperties === false) {
                    this.fail(path, 'additionalProperties', k, `unknown key: ${k}`);
                    continue;
                }
                if (s.additionalProperties !== undefined && s.additionalProperties !== true) this.check(s.additionalProperties, v, `${path}/${k}`);
            }
        }
        if (Array.isArray(s.allOf)) for (const sub of s.allOf)this.check(sub, data, path);
        if (s.if !== undefined) {
            if (this.matches(s.if, data)) {
                if (s.then !== undefined) this.check(s.then, data, path);
            } else if (s.else !== undefined) this.check(s.else, data, path);
        }
    }
    get errors() {
        return [
            ...this.errs
        ];
    }
}
export function assertKeywordCoverage(schema, path = '#') {
    const out = [];
    if (!schema || typeof schema !== 'object') return out;
    if (Array.isArray(schema)) {
        schema.forEach((s, i)=>out.push(...assertKeywordCoverage(s, `${path}/${i}`)));
        return out;
    }
    const inNameMap = /\/(properties|\$defs)$/.test(path);
    for (const [k, v] of Object.entries(schema)){
        if (!inNameMap) {
            if (!IMPLEMENTED.has(k)) {
                out.push(`${path}/${k}: keyword not implemented by this evaluator`);
                continue;
            }
            if (k === 'format' && typeof v === 'string' && !IMPLEMENTED_FORMATS.has(v)) out.push(`${path}/${k}: format '${v}' not implemented by this evaluator`);
        }
        if (k === 'enum' || k === 'required' || k === 'const') continue;
        out.push(...assertKeywordCoverage(v, `${path}/${k}`));
    }
    return out;
}
export function validate(rec, schema) {
    const gaps = assertKeywordCoverage(schema);
    if (gaps.length) {
        const e = new Error(gaps.join('; '));
        e.code = 'UNIMPLEMENTED';
        throw e;
    }
    const v = new Validator(schema, rec);
    v.check(schema, rec, '');
    return v.errors;
}
const arg = process.argv[2];
if (!arg) {
    console.error('usage: validate-seat-record.mjs <record.json> [schema.json] | --keyword-coverage <schema.json>');
    process.exit(2);
}
if (arg === '--keyword-coverage') {
    const sp = process.argv[3];
    if (!sp) {
        console.error('usage: validate-seat-record.mjs --keyword-coverage <schema.json>');
        process.exit(2);
    }
    const gaps = assertKeywordCoverage(JSON.parse(readFileSync(sp, 'utf8')));
    if (gaps.length) {
        for (const g of gaps)console.error(`  ✗ ${g}`);
        process.exit(3);
    }
    console.log('keyword coverage: every keyword occurrence in the schema is implemented here');
    process.exit(0);
}
const schemaPath = process.argv[3] ?? DEFAULT_SCHEMA;
let schemaDoc;
let parsed;
try {
    schemaDoc = JSON.parse(readFileSync(schemaPath, 'utf8'));
} catch (e) {
    console.error(`unreadable schema ${schemaPath}: ${e.message}`);
    process.exit(3);
}
try {
    parsed = JSON.parse(readFileSync(arg, 'utf8'));
} catch (e) {
    console.error(`invalid JSON: ${e.message}`);
    process.exit(1);
}
let problems;
try {
    problems = validate(parsed, schemaDoc);
} catch (e) {
    console.error(`  ✗ schema uses keywords this evaluator does not implement: ${e.message}`);
    process.exit(3);
}
if (problems.length) {
    for (const p of problems)console.error(`  ✗ ${p}`);
    process.exit(1);
}
console.log('valid');
