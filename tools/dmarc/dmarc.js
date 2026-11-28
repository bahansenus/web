/**
 * DMARC Header Analyzer — browser-only ES module port of src/dmarc_headers.py.
 *
 * Pure JavaScript, zero dependencies, no DNS lookups, no network access.
 * Produces the same object shape and analysis decisions as the Python reference.
 */

// Well-known multi-label public suffixes for offline organizational-domain extraction.
const MULTI_LABEL_PUBLIC_SUFFIXES = new Set([
  "ac.uk",
  "co.uk",
  "gov.uk",
  "ltd.uk",
  "me.uk",
  "net.uk",
  "nhs.uk",
  "org.uk",
  "plc.uk",
  "sch.uk",
  "asn.au",
  "com.au",
  "edu.au",
  "gov.au",
  "id.au",
  "net.au",
  "org.au",
  "co.nz",
  "govt.nz",
  "net.nz",
  "org.nz",
  "ac.jp",
  "co.jp",
  "ed.jp",
  "go.jp",
  "gr.jp",
  "lg.jp",
  "ne.jp",
  "or.jp",
  "com.br",
  "gov.br",
  "net.br",
  "org.br",
  "com.cn",
  "edu.cn",
  "gov.cn",
  "net.cn",
  "org.cn",
  "com.mx",
  "gob.mx",
  "net.mx",
  "org.mx",
  "co.in",
  "firm.in",
  "gen.in",
  "ind.in",
  "net.in",
  "org.in",
  "co.za",
  "gov.za",
  "net.za",
  "org.za",
  "co.kr",
  "go.kr",
  "ne.kr",
  "or.kr",
  "com.sg",
  "edu.sg",
  "gov.sg",
  "net.sg",
  "org.sg",
  "com.hk",
  "edu.hk",
  "gov.hk",
  "net.hk",
  "org.hk",
  "com.tw",
  "edu.tw",
  "gov.tw",
  "net.tw",
  "org.tw",
  "com.tr",
  "gov.tr",
  "net.tr",
  "org.tr",
  "com.ar",
  "gov.ar",
  "net.ar",
  "org.ar",
  "com.pl",
  "net.pl",
  "org.pl",
  "co.il",
  "gov.il",
  "net.il",
  "org.il",
  "com.ua",
  "gov.ua",
  "net.ua",
  "org.ua",
  "eu.org",
]);

const FOREFRONT_SCL_MEANINGS = {
  "-1": "Bypassed spam filtering (safe/allow-listed)",
  "0": "Not spam",
  "1": "Not spam",
  "5": "Spam",
  "6": "Spam",
  "7": "High confidence spam",
  "8": "High confidence spam",
  "9": "High confidence spam",
};

const FOREFRONT_CAT_MEANINGS = {
  NONE: "None",
  SPM: "Spam",
  HSPM: "High confidence spam",
  PHSH: "Phishing",
  HPHSH: "High confidence phishing",
  MALW: "Malware",
  BULK: "Bulk email",
  DIMP: "Domain impersonation",
  UIMP: "User impersonation",
  SPOOF: "Spoofing",
  GIMP: "Mailbox intelligence impersonation",
};

const HEADER_NAME_RE = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;
const POLICY_TOKEN_RE = /^[A-Za-z0-9._-]+=[A-Za-z0-9._-]+$/;
const IPV4_OR_V6_RE = /\[([0-9a-fA-F:.]+)\]/;

export const KNOWN_AUTH_METHODS = new Set([
  "spf",
  "dkim",
  "dmarc",
  "compauth",
  "arc",
  "bimi",
]);

export const FAILURE_REASON_PARTS = new Set([
  "SPF failed",
  "SPF not aligned",
  "DKIM failed",
  "DKIM not aligned",
]);

function stripChar(str, ch) {
  let start = 0;
  let end = str.length;
  while (start < end && str[start] === ch) start++;
  while (end > start && str[end - 1] === ch) end--;
  return str.slice(start, end);
}

function rstripChar(str, ch) {
  let end = str.length;
  while (end > 0 && str[end - 1] === ch) end--;
  return str.slice(0, end);
}

function splitOnce(str, sep) {
  const idx = str.indexOf(sep);
  if (idx === -1) return [str, ""];
  return [str.slice(0, idx), str.slice(idx + sep.length)];
}

function rsplitOnce(str, sep) {
  const idx = str.lastIndexOf(sep);
  if (idx === -1) return [str, ""];
  return [str.slice(0, idx), str.slice(idx + sep.length)];
}

function isDigits(str) {
  return typeof str === "string" && str.length > 0 && /^[0-9]+$/.test(str);
}

/**
 * Normalize a domain or extract the domain from an email address.
 */
export function normalizeDomain(value) {
  if (!value) return null;
  let s = String(value).trim();
  if (!s) return null;
  if (s.startsWith("<") && s.endsWith(">")) {
    s = s.slice(1, -1).trim();
  }
  if (!s) return null;
  const atIdx = s.lastIndexOf("@");
  if (atIdx !== -1) {
    s = s.slice(atIdx + 1);
  }
  s = rstripChar(stripChar(stripChar(s.trim(), '"'), "'"), ".").toLowerCase();
  if (!s || /\s/.test(s)) return null;
  return s;
}

/**
 * Return the organizational (registrable) domain using offline suffix rules.
 */
export function organizationalDomain(domain) {
  const norm = normalizeDomain(domain);
  if (!norm) return null;
  const labels = norm.split(".").filter(Boolean);
  if (labels.length <= 2) {
    return labels.join(".");
  }
  const lastTwo = labels.slice(-2).join(".");
  if (MULTI_LABEL_PUBLIC_SUFFIXES.has(lastTwo)) {
    if (labels.length >= 3) {
      return labels.slice(-3).join(".");
    }
    return lastTwo;
  }
  return lastTwo;
}

/**
 * Compare a mechanism domain against the RFC5322.From domain.
 */
export function checkAlignment(domain, fromDomain, mode = "relaxed") {
  const normDomain = normalizeDomain(domain);
  const normFrom = normalizeDomain(fromDomain);
  const orgDom = organizationalDomain(normDomain);
  const orgFrom = organizationalDomain(normFrom);
  const strict = Boolean(normDomain && normFrom && normDomain === normFrom);
  const relaxed = Boolean(orgDom && orgFrom && orgDom === orgFrom);
  const effMode = mode === "strict" ? "strict" : "relaxed";
  const aligned = effMode === "strict" ? strict : relaxed;
  return {
    domain: normDomain,
    org_domain: orgDom,
    mode: effMode,
    aligned,
    strict_aligned: strict,
    relaxed_aligned: relaxed,
  };
}

/**
 * Decode Base64 to Uint8Array safely in both browsers and Node.
 */
function base64ToBytes(b64) {
  const cleaned = b64.replace(/\s+/g, "");
  const padded =
    cleaned.length % 4 === 0
      ? cleaned
      : cleaned + "=".repeat((4 - (cleaned.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Decode RFC 2047 Q-encoding to Uint8Array.
 */
function qDecodeToBytes(qText) {
  const out = [];
  for (let i = 0; i < qText.length; i++) {
    const ch = qText[i];
    if (ch === "_") {
      out.push(0x20);
    } else if (
      ch === "=" &&
      i + 2 < qText.length &&
      /^[0-9A-Fa-f]{2}$/.test(qText.slice(i + 1, i + 3))
    ) {
      out.push(parseInt(qText.slice(i + 1, i + 3), 16));
      i += 2;
    } else {
      out.push(ch.charCodeAt(0) & 0xff);
    }
  }
  return new Uint8Array(out);
}

/**
 * Decode bytes using TextDecoder with UTF-8 fallback on unknown charsets.
 */
function decodeBytes(bytes, charset, warnings, context) {
  // Strip optional RFC 2231 language tag (e.g. "utf-8*en")
  const enc = (charset ? charset.split("*")[0].trim() : "") || "utf-8";
  try {
    return new TextDecoder(enc, { fatal: false }).decode(bytes);
  } catch {
    warnings.push(`Unknown charset '${enc}' in ${context}; fell back to utf-8`);
    return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  }
}

/**
 * Decode RFC 2047 encoded words, preserving fallback on malformed encodings.
 */
function decodeRfc2047(text, warnings, context) {
  if (text === null || text === undefined) return null;
  if (!text.includes("=?")) return text;

  try {
    // Match RFC 2047 encoded words: =?charset?encoding?encoded-text?=
    const tokenRe = /=\?([^?\s]+)\?([bBqQ])\?([^?\s]*)\?=/g;
    const segments = [];
    let lastIndex = 0;
    let match;

    while ((match = tokenRe.exec(text)) !== null) {
      if (match.index > lastIndex) {
        segments.push({ type: "text", value: text.slice(lastIndex, match.index) });
      }
      segments.push({
        type: "word",
        charset: match[1],
        encoding: match[2].toUpperCase(),
        payload: match[3],
        raw: match[0],
      });
      lastIndex = tokenRe.lastIndex;
    }
    if (lastIndex < text.length) {
      segments.push({ type: "text", value: text.slice(lastIndex) });
    }

    if (!segments.some((s) => s.type === "word")) {
      return text;
    }

    // Per RFC 2047 §6.2, linear whitespace between two consecutive encoded words is ignored.
    const filtered = [];
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      if (
        seg.type === "text" &&
        /^[ \t]+$/.test(seg.value) &&
        i > 0 &&
        i + 1 < segments.length &&
        segments[i - 1].type === "word" &&
        segments[i + 1].type === "word"
      ) {
        continue;
      }
      filtered.push(seg);
    }

    const decodedChunks = [];
    for (const seg of filtered) {
      if (seg.type === "text") {
        decodedChunks.push(seg.value);
      } else {
        try {
          const bytes =
            seg.encoding === "B"
              ? base64ToBytes(seg.payload)
              : qDecodeToBytes(seg.payload);
          decodedChunks.push(decodeBytes(bytes, seg.charset, warnings, context));
        } catch {
          decodedChunks.push(seg.raw);
        }
      }
    }
    return decodedChunks.join("");
  } catch (err) {
    warnings.push(`Failed to decode RFC 2047 value in ${context}: ${err}`);
    return text;
  }
}

/**
 * Extract header block (ignoring body) and unfold RFC 5322 continuation lines.
 */
function splitHeadersAndUnfold(rawText, warnings) {
  if (!rawText) return [];
  const text = rawText.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  let lines = text.split("\n");

  // Skip leading blank lines before headers begin (common when pasting).
  let startIdx = 0;
  while (startIdx < lines.length && lines[startIdx].trim() === "") {
    startIdx++;
  }
  lines = lines.slice(startIdx);

  // Stop at the first blank line (everything after is the message body).
  const headerLines = [];
  for (const line of lines) {
    if (line === "") break;
    headerLines.push(line);
  }

  const unfolded = [];
  for (let i = 0; i < headerLines.length; i++) {
    const lineNo = i + 1;
    const line = headerLines[i];
    if (line[0] === " " || line[0] === "\t") {
      if (unfolded.length === 0) {
        warnings.push(
          `Orphan continuation line at header line ${lineNo}: '${line.trim()}'`
        );
        continue;
      }
      const prev = unfolded[unfolded.length - 1];
      unfolded[unfolded.length - 1] = [prev[0], `${prev[1]} ${line.trim()}`];
    } else {
      const firstWord = splitOnce(line, " ")[0];
      if (lineNo === 1 && line.startsWith("From ") && !firstWord.includes(":")) {
        warnings.push("Ignored mbox 'From ' envelope line at top of input");
        continue;
      }
      if (!line.includes(":")) {
        warnings.push(
          `Malformed header line ${lineNo} (missing ':'): '${line}'`
        );
        continue;
      }
      const [name, value] = splitOnce(line, ":");
      const nameStripped = name.trim();
      if (!nameStripped || !HEADER_NAME_RE.test(nameStripped)) {
        warnings.push(`Malformed header name at line ${lineNo}: '${name}'`);
        continue;
      }
      unfolded.push([nameStripped, value.trim()]);
    }
  }
  return unfolded;
}

/**
 * Unquote an RFC 5322 quoted-string if wrapped in matching double quotes.
 */
function unquoteDisplayName(raw) {
  const s = raw.trim();
  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
    return s.slice(1, -1).replace(/\\(.)/g, "$1");
  }
  return s;
}

/**
 * Parse a single RFC 5322 mailbox into [displayName, addrSpec], mirroring
 * Python's email.utils.parseaddr() for standard, quoted, and malformed inputs.
 */
function parseAddrPair(rawValue) {
  const s = String(rawValue || "").trim();
  if (!s) return ["", ""];

  // Scan top-level structure tracking quotes and comments.
  let inQuote = false;
  let escaped = false;
  let parenDepth = 0;
  let angleStart = -1;
  let angleEnd = -1;

  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (ch === "\\" && (inQuote || parenDepth > 0)) {
      escaped = true;
      continue;
    }
    if (parenDepth > 0) {
      if (ch === "(") parenDepth++;
      else if (ch === ")") parenDepth--;
      continue;
    }
    if (ch === '"') {
      inQuote = !inQuote;
      continue;
    }
    if (!inQuote) {
      if (ch === "(") {
        parenDepth = 1;
        continue;
      }
      if (ch === "<" && angleStart === -1) {
        angleStart = i;
      } else if (ch === ">" && angleStart !== -1 && angleEnd === -1) {
        angleEnd = i;
        break;
      }
    }
  }

  // Unclosed leading quote: mirrors Python email.utils.parseaddr behavior where
  // the leading quote is consumed and the remainder becomes the address token.
  if (inQuote && s.startsWith('"') && angleStart === -1) {
    return ["", s.slice(1).trim()];
  }

  if (angleStart !== -1 && angleEnd !== -1 && angleEnd > angleStart) {
    const before = s.slice(0, angleStart).trim();
    const addr = s.slice(angleStart + 1, angleEnd).trim();
    const displayName = before ? unquoteDisplayName(before) : "";
    return [displayName, addr];
  }

  // Bare address with optional parenthetical comment: user@example.com (Display Name)
  const commentMatch = s.match(/^([^\s(]+@[^\s()]+)\s*\(([^)]*)\)\s*$/);
  if (commentMatch) {
    return [commentMatch[2].trim(), commentMatch[1].trim()];
  }

  return ["", s];
}

/**
 * Split a comma-separated RFC 5322 address list outside quotes, comments, and angle brackets.
 */
function splitAddressList(rawValue) {
  const parts = [];
  let buf = "";
  let inQuote = false;
  let escaped = false;
  let parenDepth = 0;
  let inAngle = false;

  for (const ch of String(rawValue || "")) {
    if (escaped) {
      buf += ch;
      escaped = false;
      continue;
    }
    if (ch === "\\" && (inQuote || parenDepth > 0)) {
      buf += ch;
      escaped = true;
      continue;
    }
    if (ch === '"' && parenDepth === 0) {
      inQuote = !inQuote;
      buf += ch;
      continue;
    }
    if (!inQuote) {
      if (ch === "(") {
        parenDepth++;
        buf += ch;
        continue;
      }
      if (ch === ")" && parenDepth > 0) {
        parenDepth--;
        buf += ch;
        continue;
      }
      if (parenDepth === 0) {
        if (ch === "<") {
          inAngle = true;
        } else if (ch === ">") {
          inAngle = false;
        } else if (ch === "," && !inAngle) {
          if (buf.trim()) parts.push(buf.trim());
          buf = "";
          continue;
        }
      }
    }
    buf += ch;
  }
  if (buf.trim()) parts.push(buf.trim());
  return parts;
}

/**
 * Parse a single mailbox header value (From, Reply-To).
 */
function parseSingleAddress(rawValue, warnings, fieldName) {
  const [rawName, addr] = parseAddrPair(rawValue);
  const rawDisplay = rawName ? rawName : null;
  const decodedDisplay = rawDisplay
    ? decodeRfc2047(rawDisplay, warnings, fieldName)
    : null;
  const trimmedAddr = addr ? addr.trim() : "";
  const address = trimmedAddr || null;
  const domain =
    address && address.includes("@") ? normalizeDomain(address) : null;
  if (!address) {
    warnings.push(
      `Could not extract email address from ${fieldName}: '${rawValue}'`
    );
  }
  return {
    raw: rawValue,
    display_name: decodedDisplay,
    raw_display_name: rawDisplay,
    address,
    domain,
  };
}

/**
 * Parse one or more headers containing comma-separated address lists.
 */
function parseAddressList(rawValues, warnings, fieldName) {
  const results = [];
  for (const rawVal of rawValues) {
    const items = splitAddressList(rawVal);
    for (const item of items) {
      const [rawName, addr] = parseAddrPair(item);
      const rawDisplay = rawName ? rawName : null;
      const decodedDisplay = rawDisplay
        ? decodeRfc2047(rawDisplay, warnings, fieldName)
        : null;
      const address = addr ? addr.trim() : null;
      const domain =
        address && address.includes("@") ? normalizeDomain(address) : null;
      results.push({
        raw: rawVal,
        display_name: decodedDisplay,
        raw_display_name: rawDisplay,
        address: address || null,
        domain,
      });
    }
  }
  return results;
}

/**
 * Parse Return-Path header (envelope sender).
 */
function parseReturnPath(rawValue) {
  const stripped = rawValue.trim();
  if (stripped === "<>") {
    return { raw: rawValue, address: "", domain: null };
  }
  const [, addr] = parseAddrPair(stripped);
  const address = addr ? addr.trim() : stripped.replace(/^<+|>+$/g, "").trim();
  const domain =
    address && address.includes("@") ? normalizeDomain(address) : null;
  return {
    raw: rawValue,
    address: address || null,
    domain,
  };
}

const MONTH_MAP = {
  jan: 1,
  feb: 2,
  mar: 3,
  apr: 4,
  may: 5,
  jun: 6,
  jul: 7,
  aug: 8,
  sep: 9,
  oct: 10,
  nov: 11,
  dec: 12,
};

const TZ_OFFSETS_MIN = {
  UT: 0,
  UTC: 0,
  GMT: 0,
  Z: 0,
  EST: -300,
  EDT: -240,
  CST: -360,
  CDT: -300,
  MST: -420,
  MDT: -360,
  PST: -480,
  PDT: -420,
};

function pad2(n) {
  return String(n).padStart(2, "0");
}

function formatOffset(offsetMin) {
  const sign = offsetMin < 0 ? "-" : "+";
  const abs = Math.abs(offsetMin);
  const hh = Math.floor(abs / 60);
  const mm = abs % 60;
  return `${sign}${pad2(hh)}:${pad2(mm)}`;
}

/**
 * Parse an RFC 5322 date string into ISO 8601 and POSIX timestamp (seconds).
 */
function parseDate(rawValue, warnings, context) {
  const cleaned = String(rawValue || "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  // RFC 5322 date-time pattern: [Day,] DD Mon YYYY HH:MM[:SS] [TZ]
  const m = cleaned.match(
    /^(?:[A-Za-z]{3},\s*)?(\d{1,2})\s+([A-Za-z]{3})\s+(\d{2,4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s+([+-]\d{4}|[A-Za-z]{1,5}))?$/
  );

  if (m) {
    const day = parseInt(m[1], 10);
    const month = MONTH_MAP[m[2].toLowerCase()];
    let year = parseInt(m[3], 10);
    if (year < 100) {
      year += year >= 50 ? 1900 : 2000;
    }
    const hour = parseInt(m[4], 10);
    const minute = parseInt(m[5], 10);
    const second = m[6] !== undefined ? parseInt(m[6], 10) : 0;
    const tzToken = m[7];

    if (
      month &&
      day >= 1 &&
      day <= 31 &&
      hour <= 23 &&
      minute <= 59 &&
      second <= 60
    ) {
      let offsetMin = null;
      if (tzToken) {
        if (/^[+-]\d{4}$/.test(tzToken)) {
          const sign = tzToken[0] === "-" ? -1 : 1;
          const tzH = parseInt(tzToken.slice(1, 3), 10);
          const tzM = parseInt(tzToken.slice(3, 5), 10);
          offsetMin = sign * (tzH * 60 + tzM);
        } else if (Object.prototype.hasOwnProperty.call(TZ_OFFSETS_MIN, tzToken.toUpperCase())) {
          offsetMin = TZ_OFFSETS_MIN[tzToken.toUpperCase()];
        }
      }

      const utcMs =
        Date.UTC(year, month - 1, day, hour, minute, second) -
        (offsetMin !== null ? offsetMin * 60 * 1000 : 0);
      if (!Number.isNaN(utcMs)) {
        const tzSuffix = offsetMin !== null ? formatOffset(offsetMin) : "";
        const iso = `${String(year).padStart(4, "0")}-${pad2(month)}-${pad2(day)}T${pad2(hour)}:${pad2(minute)}:${pad2(second)}${tzSuffix}`;
        return {
          raw: rawValue,
          iso,
          timestamp: utcMs / 1000,
        };
      }
    }
  }

  // Fallback to Date.parse for non-standard date strings
  const ms = Date.parse(cleaned);
  if (!Number.isNaN(ms)) {
    const dt = new Date(ms);
    return {
      raw: rawValue,
      iso: dt.toISOString().replace(/\.\d{3}Z$/, "+00:00"),
      timestamp: ms / 1000,
    };
  }

  warnings.push(`Could not parse date in ${context}: '${rawValue}'`);
  return { raw: rawValue, iso: null, timestamp: null };
}

/**
 * Parse semicolon-separated tag=value pairs (DKIM-Signature, ARC-Seal, etc.).
 */
function parseTagList(rawValue) {
  const tags = {};
  for (const partRaw of rawValue.split(";")) {
    const part = partRaw.trim();
    if (!part || !part.includes("=")) continue;
    const [k, v] = splitOnce(part, "=");
    const key = k.trim().toLowerCase();
    const val = v.trim();
    if (key) {
      tags[key] = val;
    }
  }
  return tags;
}

/**
 * Parse a DKIM-Signature header extracting v, a, c, d, s, bh, h, t, x, b.
 */
function parseDkimSignature(rawValue, warnings) {
  const tags = parseTagList(rawValue);
  if (Object.keys(tags).length === 0) {
    warnings.push(`Malformed DKIM-Signature header: '${rawValue}'`);
  }
  const bh = "bh" in tags ? tags.bh.replace(/\s+/g, "") : null;
  const bVal = "b" in tags ? tags.b.replace(/\s+/g, "") : null;
  const hVal = "h" in tags ? tags.h.replace(/\s+/g, "") : null;
  const domain = normalizeDomain(tags.d ?? null);
  return {
    v: tags.v ?? null,
    a: tags.a ?? null,
    c: tags.c ?? null,
    d: domain,
    s: tags.s ?? null,
    bh,
    h: hVal,
    t: tags.t ?? null,
    x: tags.x ?? null,
    b: bVal,
    tags,
    raw: rawValue,
  };
}

/**
 * Split text on `sep` while ignoring separators inside (...) or "...".
 */
function splitRespectingCommentsAndQuotes(text, sep = ";") {
  const parts = [];
  let buf = "";
  let parenDepth = 0;
  let inQuote = false;
  let escaped = false;

  for (const ch of text) {
    if (escaped) {
      buf += ch;
      escaped = false;
      continue;
    }
    if (ch === "\\" && (inQuote || parenDepth > 0)) {
      buf += ch;
      escaped = true;
      continue;
    }
    if (ch === '"' && parenDepth === 0) {
      inQuote = !inQuote;
      buf += ch;
      continue;
    }
    if (!inQuote) {
      if (ch === "(") {
        parenDepth++;
        buf += ch;
        continue;
      }
      if (ch === ")" && parenDepth > 0) {
        parenDepth--;
        buf += ch;
        continue;
      }
      if (ch === sep && parenDepth === 0) {
        parts.push(buf.trim());
        buf = "";
        continue;
      }
    }
    buf += ch;
  }
  parts.push(buf.trim());
  return parts;
}

/**
 * Tokenize an Authentication-Results resinfo segment into [tokens, comments].
 */
function tokenizeResinfo(segment) {
  const tokens = [];
  const comments = [];
  let buf = "";
  let commentBuf = "";
  let parenDepth = 0;
  let inQuote = false;
  let escaped = false;

  function flushToken() {
    if (buf.length > 0) {
      tokens.push(buf);
      buf = "";
    }
  }

  for (const ch of segment) {
    if (escaped) {
      if (parenDepth > 0) {
        commentBuf += ch;
      } else {
        buf += ch;
      }
      escaped = false;
      continue;
    }
    if (ch === "\\" && (inQuote || parenDepth > 0)) {
      escaped = true;
      continue;
    }
    if (parenDepth > 0) {
      if (ch === "(") {
        parenDepth++;
        commentBuf += ch;
      } else if (ch === ")") {
        parenDepth--;
        if (parenDepth === 0) {
          const cStr = commentBuf.trim();
          if (cStr) comments.push(cStr);
          commentBuf = "";
        } else {
          commentBuf += ch;
        }
      } else {
        commentBuf += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuote = !inQuote;
      buf += ch;
      continue;
    }
    if (!inQuote && ch === "(") {
      flushToken();
      parenDepth = 1;
      continue;
    }
    if (!inQuote && /\s/.test(ch)) {
      flushToken();
      continue;
    }
    buf += ch;
  }

  flushToken();
  if (commentBuf.length > 0) {
    const cStr = commentBuf.trim();
    if (cStr) comments.push(cStr);
  }
  return [tokens, comments];
}

/**
 * If a parenthetical comment consists exclusively of key=val policy pairs, parse them.
 */
function parsePolicyComment(comment) {
  const trimmed = comment.trim();
  if (!trimmed) return null;
  const pieces = trimmed.split(/\s+/);
  if (pieces.length === 0) return null;
  if (pieces.every((p) => POLICY_TOKEN_RE.test(p))) {
    const policy = {};
    for (const p of pieces) {
      const [k, v] = splitOnce(p, "=");
      policy[k.toLowerCase()] = v.toLowerCase();
    }
    return policy;
  }
  return null;
}

/**
 * Return [domain, sourceProperty] for a parsed A-R method entry.
 */
function extractEntryDomain(method, properties) {
  let propsToTry;
  if (method === "spf") {
    propsToTry = ["smtp.mailfrom", "smtp.helo", "header.from"];
  } else if (method === "dkim") {
    propsToTry = ["header.d", "header.i"];
  } else if (method === "dmarc") {
    propsToTry = ["header.from", "policy.dmarc"];
  } else if (method === "arc" || method === "bimi") {
    propsToTry = ["header.d", "header.from", "smtp.mailfrom"];
  } else {
    propsToTry = ["header.from", "header.d", "smtp.mailfrom"];
  }

  for (const prop of propsToTry) {
    if (Object.prototype.hasOwnProperty.call(properties, prop)) {
      const dom = normalizeDomain(properties[prop]);
      if (dom) return [dom, prop];
    }
  }
  return [null, null];
}

/**
 * Parse one Authentication-Results (or ARC-Authentication-Results body) header.
 */
function parseAuthResultsHeader(
  rawValue,
  index,
  warnings,
  headerName = "Authentication-Results"
) {
  const segments = splitRespectingCommentsAndQuotes(rawValue, ";");
  if (segments.length === 0) {
    warnings.push(`Empty ${headerName} header`);
    return {
      index,
      is_authoritative: false,
      authserv_id: null,
      raw: rawValue,
      results: [],
    };
  }

  // First segment is authserv-id [version]
  const [authservTokens] = tokenizeResinfo(segments[0]);
  const authservId =
    authservTokens.length > 0 ? stripChar(authservTokens[0], '"') : null;
  if (!authservId) {
    warnings.push(`Missing authserv-id in ${headerName}: '${rawValue}'`);
  }

  const results = [];
  for (const seg of segments.slice(1)) {
    const segStripped = seg.trim();
    if (!segStripped || segStripped.toLowerCase() === "none") continue;
    const [tokens, comments] = tokenizeResinfo(segStripped);
    if (tokens.length === 0) continue;

    const first = tokens[0];
    if (!first.includes("=")) {
      warnings.push(
        `Unparseable ${headerName} entry (missing '='): '${segStripped}'`
      );
      continue;
    }
    const [rawMethod, rawResult] = splitOnce(first, "=");
    const method = splitOnce(rawMethod, "/")[0].trim().toLowerCase();
    const result = stripChar(rawResult.trim(), '"').toLowerCase();
    if (!method || !result) {
      warnings.push(
        `Malformed ${headerName} method/result token: '${first}'`
      );
      continue;
    }

    const properties = {};
    const extraReasonTokens = [];
    for (const tok of tokens.slice(1)) {
      if (tok.includes("=")) {
        const [pk, pv] = splitOnce(tok, "=");
        const pkNorm = pk.trim().toLowerCase();
        const pvNorm = stripChar(pv.trim(), '"');
        if (pkNorm) {
          properties[pkNorm] = pvNorm;
        }
      } else {
        extraReasonTokens.push(stripChar(tok, '"'));
      }
    }

    // Separate policy tags in comments from human-readable reason comments
    const policy = {};
    const reasonComments = [];
    for (const c of comments) {
      const parsedPol = parsePolicyComment(c);
      if (parsedPol !== null && method === "dmarc") {
        Object.assign(policy, parsedPol);
      } else {
        reasonComments.push(c);
      }
    }

    // Also merge policy.* properties into policy dict
    for (const [pk, pv] of Object.entries(properties)) {
      if (pk.startsWith("policy.")) {
        policy[splitOnce(pk, ".")[1]] = pv.toLowerCase();
      }
    }

    let reason = properties.reason ?? null;
    if (!reason && reasonComments.length > 0) {
      reason = reasonComments.join("; ");
    } else if (!reason && extraReasonTokens.length > 0) {
      reason = extraReasonTokens.join(" ");
    }

    const [domain, sourceProp] = extractEntryDomain(method, properties);
    const entry = {
      method,
      result,
      domain,
      source_property: sourceProp,
      reason,
      comments,
      properties,
      raw: segStripped,
    };
    if (Object.keys(policy).length > 0) {
      entry.policy = policy;
    }
    results.push(entry);
  }

  return {
    index,
    is_authoritative: false,
    authserv_id: authservId || null,
    raw: rawValue,
    results,
  };
}

/**
 * Parse a Received-SPF header (RFC 7208).
 */
function parseReceivedSpf(rawValue, warnings) {
  const [tokens, comments] = tokenizeResinfo(rawValue);
  if (tokens.length === 0) {
    warnings.push(`Empty Received-SPF header: '${rawValue}'`);
    return {
      result: "unknown",
      domain: null,
      comment: null,
      properties: {},
      raw: rawValue,
    };
  }
  const result = rstripChar(tokens[0], ";").toLowerCase();
  const properties = {};
  for (const seg of splitRespectingCommentsAndQuotes(rawValue, ";")) {
    const [segTokens] = tokenizeResinfo(seg);
    for (const tok of segTokens) {
      if (tok.includes("=")) {
        const [k, v] = splitOnce(tok, "=");
        properties[k.trim().toLowerCase()] = stripChar(v.trim(), '"');
      }
    }
  }
  let domain = null;
  for (const prop of ["envelope-from", "identity", "helo"]) {
    if (Object.prototype.hasOwnProperty.call(properties, prop)) {
      const dom = normalizeDomain(properties[prop]);
      if (dom) {
        domain = dom;
        break;
      }
    }
  }
  return {
    result,
    domain,
    client_ip: properties["client-ip"] ?? null,
    helo: properties.helo ?? null,
    envelope_from: properties["envelope-from"] ?? null,
    receiver: properties.receiver ?? null,
    comment: comments.length > 0 ? comments.join("; ") : null,
    properties,
    raw: rawValue,
  };
}

/**
 * Parse Microsoft X-Forefront-Antispam-Report header (SCL/BCL/CAT).
 */
function parseForefrontReport(rawValue) {
  const fields = {};
  for (const partRaw of rawValue.split(";")) {
    const part = partRaw.trim();
    if (!part || !part.includes(":")) continue;
    const [k, v] = splitOnce(part, ":");
    const key = k.trim().toUpperCase();
    const val = v.trim();
    if (key) fields[key] = val;
  }

  let scl = null;
  let sclMeaning = null;
  if ("SCL" in fields) {
    if (/^-?\d+$/.test(fields.SCL)) {
      scl = parseInt(fields.SCL, 10);
      sclMeaning =
        FOREFRONT_SCL_MEANINGS[String(scl)] ?? `SCL ${scl}`;
    } else {
      sclMeaning = fields.SCL;
    }
  }

  let bcl = null;
  if ("BCL" in fields) {
    bcl = /^-?\d+$/.test(fields.BCL) ? parseInt(fields.BCL, 10) : null;
  }

  const cat = fields.CAT ?? null;
  const catMeaning = cat
    ? FOREFRONT_CAT_MEANINGS[cat.toUpperCase()] ?? cat
    : null;

  return {
    scl,
    scl_meaning: sclMeaning,
    bcl,
    cat,
    cat_meaning: catMeaning,
    cip: fields.CIP ?? null,
    ctry: fields.CTRY ?? null,
    sfv: fields.SFV ?? null,
    fields,
    raw: rawValue,
  };
}

/**
 * Parse Received headers (document order = reverse chronological) with hop delays.
 */
function parseReceived(rawValues, warnings) {
  const hops = [];
  for (let idx = 0; idx < rawValues.length; idx++) {
    const raw = rawValues[idx];
    let routePart;
    let dateInfo;
    if (raw.includes(";")) {
      const [rp, dp] = rsplitOnce(raw, ";");
      routePart = rp;
      dateInfo = parseDate(dp.trim(), warnings, `Received[${idx}]`);
    } else {
      routePart = raw;
      dateInfo = { raw: null, iso: null, timestamp: null };
    }

    const fromMatch = routePart.match(/\bfrom\s+([^\s(]+)/i);
    const byMatch = routePart.match(/\bby\s+([^\s(]+)/i);
    const withMatch = routePart.match(/\bwith\s+([^\s;]+)/i);
    const idMatch = routePart.match(/\bid\s+([^\s;]+)/i);
    const forMatch = routePart.match(/\bfor\s+<?([^>\s;]+)>?/i);
    const ipMatch = routePart.match(IPV4_OR_V6_RE);

    hops.push({
      index: idx,
      from_host: fromMatch ? fromMatch[1] : null,
      by_host: byMatch ? byMatch[1] : null,
      with_protocol: withMatch ? withMatch[1] : null,
      id: idMatch ? idMatch[1] : null,
      for_address: forMatch ? forMatch[1] : null,
      ip: ipMatch ? ipMatch[1] : null,
      date_raw: dateInfo.raw,
      date_iso: dateInfo.iso,
      timestamp: dateInfo.timestamp,
      delay_seconds: null,
      raw,
    });
  }

  // Received headers are prepended (index 0 is newest, index N-1 is oldest).
  // Delay at hop i = timestamp[i] - timestamp[i + 1].
  for (let i = 0; i < hops.length - 1; i++) {
    const tCur = hops[i].timestamp;
    const tPrev = hops[i + 1].timestamp;
    if (tCur !== null && tPrev !== null) {
      hops[i].delay_seconds = Math.round((tCur - tPrev) * 1000) / 1000;
    }
  }

  return hops;
}

/**
 * Parse ARC-Seal, ARC-Message-Signature, and ARC-Authentication-Results headers.
 */
function parseArc(sealsRaw, amsRaw, aarRaw, warnings) {
  const seals = sealsRaw.map((v) => parseTagList(v));
  const ams = amsRaw.map((v) => parseTagList(v));
  const aars = [];
  const instanceIds = new Set();

  for (const item of [...seals, ...ams]) {
    if ("i" in item && isDigits(item.i)) {
      instanceIds.add(parseInt(item.i, 10));
    }
  }

  for (let idx = 0; idx < aarRaw.length; idx++) {
    const raw = aarRaw[idx];
    const parts = splitRespectingCommentsAndQuotes(raw, ";");
    let inst = null;
    let restRaw = raw;
    if (parts.length > 0 && parts[0].toLowerCase().startsWith("i=")) {
      const iStr = splitOnce(parts[0], "=")[1].trim();
      if (isDigits(iStr)) {
        inst = parseInt(iStr, 10);
        instanceIds.add(inst);
      }
      restRaw = parts.slice(1).join("; ");
    }
    const parsedAr = parseAuthResultsHeader(
      restRaw,
      idx,
      warnings,
      "ARC-Authentication-Results"
    );
    parsedAr.i = inst;
    parsedAr.raw = raw;
    aars.push(parsedAr);
  }

  const present = seals.length > 0 || ams.length > 0 || aars.length > 0;
  const sortedInstances = Array.from(instanceIds).sort((a, b) => a - b);
  return {
    present,
    instance_count:
      instanceIds.size > 0
        ? instanceIds.size
        : Math.max(seals.length, ams.length, aars.length),
    instances: sortedInstances,
    seal_count: seals.length,
    message_signature_count: ams.length,
    auth_results_count: aars.length,
    seals,
    message_signatures: ams,
    auth_results: aars,
  };
}

/**
 * Compute SPF/DKIM alignment and DMARC verdict with provenance and disagreement checks.
 */
function evaluateAlignmentAndDmarc({
  fromDomain,
  authResults,
  dkimSignatures,
  receivedSpf,
  warnings,
}) {
  const authoritative = authResults.length > 0 ? authResults[0] : null;
  if (authoritative !== null) {
    authoritative.is_authoritative = true;
  }

  const arEntries = authoritative ? authoritative.results : [];
  const spfArEntries = arEntries.filter((e) => e.method === "spf");
  const dkimArEntries = arEntries.filter((e) => e.method === "dkim");
  const dmarcArEntries = arEntries.filter((e) => e.method === "dmarc");

  // Alignment modes from DMARC policy tags if explicitly present (default: relaxed)
  const dmarcEntry = dmarcArEntries.length > 0 ? dmarcArEntries[0] : null;
  const rawDmarcPolicy =
    dmarcEntry && dmarcEntry.policy ? { ...dmarcEntry.policy } : {};
  const dmarcPolicy = {
    p: null,
    sp: null,
    dis: null,
    ...rawDmarcPolicy,
  };
  const aspfMode = dmarcPolicy.aspf === "s" ? "strict" : "relaxed";
  const adkimMode = dmarcPolicy.adkim === "s" ? "strict" : "relaxed";

  // --- SPF alignment ---
  let spfSection;
  if (spfArEntries.length > 0) {
    const spfPrimary = spfArEntries[0];
    const spfCheck = checkAlignment(spfPrimary.domain, fromDomain, aspfMode);
    const spfPassesDmarc = spfPrimary.result === "pass" && spfCheck.aligned;
    spfSection = {
      result: spfPrimary.result,
      ...spfCheck,
      passes_dmarc: spfPassesDmarc,
      provenance: "per-auth-results",
      source_property: spfPrimary.source_property,
      reason: spfPrimary.reason,
    };
  } else {
    const spfCheck = checkAlignment(null, fromDomain, aspfMode);
    spfSection = {
      result: "unknown",
      ...spfCheck,
      passes_dmarc: false,
      provenance: "unknown",
      source_property: null,
      reason: null,
    };
  }

  // Check Received-SPF disagreement against authoritative A-R SPF
  if (receivedSpf.length > 0 && spfArEntries.length > 0) {
    const arSpfRes = spfArEntries[0].result;
    for (const rspf of receivedSpf) {
      const disagrees = rspf.result !== "unknown" && rspf.result !== arSpfRes;
      rspf.disagrees_with_auth_results = disagrees;
      if (disagrees) {
        warnings.push(
          `Received-SPF (${rspf.result}) disagrees with Authentication-Results SPF (${arSpfRes})`
        );
      }
    }
  } else {
    for (const rspf of receivedSpf) {
      rspf.disagrees_with_auth_results = false;
    }
  }

  // --- DKIM alignment ---
  const dkimEvaluated = [];
  let dkimAggResult;
  let dkimAggAligned;
  let dkimAggStrict;
  let dkimAggRelaxed;
  let dkimPassesDmarc;
  let dkimProvenance;

  if (dkimArEntries.length > 0) {
    for (const entry of dkimArEntries) {
      const dkimCheck = checkAlignment(entry.domain, fromDomain, adkimMode);
      const passesDmarc = entry.result === "pass" && dkimCheck.aligned;
      dkimEvaluated.push({
        result: entry.result,
        ...dkimCheck,
        selector: entry.properties["header.s"] ?? null,
        passes_dmarc: passesDmarc,
        provenance: "per-auth-results",
        reason: entry.reason,
      });
    }
    const passingEntries = dkimEvaluated.filter((e) => e.result === "pass");
    if (passingEntries.length > 0) {
      dkimAggResult = "pass";
      dkimAggAligned = passingEntries.some((e) => e.aligned);
      dkimAggStrict = passingEntries.some((e) => e.strict_aligned);
      dkimAggRelaxed = passingEntries.some((e) => e.relaxed_aligned);
      dkimPassesDmarc = passingEntries.some((e) => e.passes_dmarc);
    } else {
      dkimAggResult = dkimEvaluated[0].result;
      dkimAggAligned = dkimEvaluated.some((e) => e.aligned);
      dkimAggStrict = dkimEvaluated.some((e) => e.strict_aligned);
      dkimAggRelaxed = dkimEvaluated.some((e) => e.relaxed_aligned);
      dkimPassesDmarc = false;
    }
    dkimProvenance = "per-auth-results";
  } else if (dkimSignatures.length > 0) {
    for (const sig of dkimSignatures) {
      const dkimCheck = checkAlignment(sig.d, fromDomain, adkimMode);
      dkimEvaluated.push({
        result: "unknown",
        ...dkimCheck,
        selector: sig.s,
        passes_dmarc: false,
        provenance: "signature-present-unverified",
        reason: "DKIM-Signature present but no Authentication-Results verification",
      });
    }
    dkimAggResult = "unknown";
    dkimAggAligned = dkimEvaluated.some((e) => e.aligned);
    dkimAggStrict = dkimEvaluated.some((e) => e.strict_aligned);
    dkimAggRelaxed = dkimEvaluated.some((e) => e.relaxed_aligned);
    dkimPassesDmarc = false;
    dkimProvenance = "signature-present-unverified";
  } else {
    dkimAggResult = "unknown";
    dkimAggAligned = false;
    dkimAggStrict = false;
    dkimAggRelaxed = false;
    dkimPassesDmarc = false;
    dkimProvenance = "unknown";
  }

  const dkimSection = {
    result: dkimAggResult,
    mode: adkimMode,
    aligned: dkimAggAligned,
    strict_aligned: dkimAggStrict,
    relaxed_aligned: dkimAggRelaxed,
    passes_dmarc: dkimPassesDmarc,
    provenance: dkimProvenance,
    entries: dkimEvaluated,
  };

  const alignment = {
    from_domain: fromDomain,
    from_org_domain: organizationalDomain(fromDomain),
    spf: spfSection,
    dkim: dkimSection,
  };

  // --- Computed DMARC verdict from A-R SPF/DKIM inputs ---
  const hasArInputs = spfArEntries.length > 0 || dkimArEntries.length > 0;
  let computedResult;
  let computedReason;

  if (!hasArInputs) {
    computedResult = "unknown";
    computedReason =
      authResults.length === 0
        ? "No Authentication-Results header present"
        : "No SPF or DKIM results in Authentication-Results";
  } else if (spfSection.passes_dmarc || dkimSection.passes_dmarc) {
    computedResult = "pass";
    computedReason = null;
  } else {
    computedResult = "fail";
    const reasonParts = [];
    if (spfArEntries.length > 0) {
      if (spfSection.result === "pass") {
        reasonParts.push("SPF not aligned");
      } else {
        reasonParts.push("SPF failed");
      }
    }
    if (dkimArEntries.length > 0) {
      if (dkimSection.result === "pass") {
        reasonParts.push("DKIM not aligned");
      } else {
        reasonParts.push("DKIM failed");
      }
    }
    computedReason =
      reasonParts.length > 0
        ? reasonParts.join(", ")
        : "SPF failed, DKIM failed";
  }

  // --- Combine reported DMARC vs computed DMARC ---
  let reportedInfo = null;
  let disagreement = false;
  let disagreementDetail = null;
  let finalResult;
  let finalReason;
  let finalProvenance;
  let dmarcDomain;

  if (dmarcEntry !== null) {
    const reportedResult = dmarcEntry.result;
    const reportedReason = dmarcEntry.reason;
    const reportedDomain = dmarcEntry.domain || fromDomain;
    reportedInfo = {
      result: reportedResult,
      reason: reportedReason,
      policy: dmarcPolicy,
      domain: reportedDomain,
      authserv_id: authoritative ? authoritative.authserv_id : null,
    };

    finalResult = reportedResult;
    finalProvenance = "per-auth-results";
    if (reportedResult === "pass") {
      finalReason = null;
    } else if (reportedReason) {
      finalReason = reportedReason;
    } else if (computedResult === "fail" && computedReason) {
      finalReason = computedReason;
    } else {
      finalReason = null;
    }

    if (
      (computedResult === "pass" || computedResult === "fail") &&
      (reportedResult === "pass" || reportedResult === "fail") &&
      reportedResult !== computedResult
    ) {
      disagreement = true;
      disagreementDetail =
        `Authentication-Results reports dmarc=${reportedResult}` +
        (reportedReason ? ` (${reportedReason})` : "") +
        `, but computed DMARC from A-R inputs is ${computedResult}` +
        (computedReason ? ` (${computedReason})` : "");
      warnings.push(`DMARC disagreement: ${disagreementDetail}`);
    }

    dmarcDomain = reportedDomain;
  } else if (hasArInputs) {
    finalResult = computedResult;
    finalReason = computedReason;
    finalProvenance = "computed";
    dmarcDomain = fromDomain;
  } else {
    finalResult = "unknown";
    finalReason = computedReason;
    finalProvenance = "unknown";
    dmarcDomain = fromDomain;
  }

  const dmarc = {
    result: finalResult,
    reason: finalReason,
    provenance: finalProvenance,
    domain: dmarcDomain,
    policy: dmarcPolicy,
    reported: reportedInfo,
    computed: {
      result: computedResult,
      reason: computedReason,
    },
    disagreement,
    disagreement_detail: disagreementDetail,
  };

  return { alignment, dmarc };
}

/**
 * Parse raw email headers and perform offline DMARC alignment analysis.
 * Returns the exact same object shape as Python's parse_headers().
 */
export function parseHeaders(rawText) {
  const warnings = [];
  let text = rawText;
  if (typeof text !== "string") {
    warnings.push("Input was not a string; coerced to str");
    text = text === null || text === undefined ? "" : String(text);
  }

  const headers = splitHeadersAndUnfold(text, warnings);

  const byName = new Map();
  for (const [name, value] of headers) {
    const key = name.toLowerCase();
    if (!byName.has(key)) byName.set(key, []);
    byName.get(key).push(value);
  }

  // From
  const fromVals = byName.get("from") || [];
  if (fromVals.length > 1) {
    warnings.push(
      `Multiple From headers found (${fromVals.length}); using the first`
    );
  }
  let fromInfo;
  if (fromVals.length > 0) {
    fromInfo = parseSingleAddress(fromVals[0], warnings, "From");
  } else {
    warnings.push("Missing From header");
    fromInfo = {
      raw: null,
      display_name: null,
      raw_display_name: null,
      address: null,
      domain: null,
    };
  }

  // Reply-To
  const replyToVals = byName.get("reply-to") || [];
  const replyToInfo =
    replyToVals.length > 0
      ? parseSingleAddress(replyToVals[0], warnings, "Reply-To")
      : null;

  // Return-Path
  const returnPathVals = byName.get("return-path") || [];
  const returnPathInfo =
    returnPathVals.length > 0 ? parseReturnPath(returnPathVals[0]) : null;

  // To
  const toInfo = parseAddressList(byName.get("to") || [], warnings, "To");

  // Subject
  const subjectVals = byName.get("subject") || [];
  const subjectInfo =
    subjectVals.length > 0
      ? {
          raw: subjectVals[0],
          decoded: decodeRfc2047(subjectVals[0], warnings, "Subject"),
        }
      : null;

  // Date
  const dateVals = byName.get("date") || [];
  const dateInfo =
    dateVals.length > 0 ? parseDate(dateVals[0], warnings, "Date") : null;

  // Message-ID
  const msgIdVals = byName.get("message-id") || [];
  const messageId = msgIdVals.length > 0 ? msgIdVals[0] : null;

  // Authentication-Results (preserve all in document order; topmost is authoritative)
  const authResults = (byName.get("authentication-results") || []).map(
    (val, idx) => parseAuthResultsHeader(val, idx, warnings)
  );

  // DKIM-Signature (preserve all in document order)
  const dkimSignatures = (byName.get("dkim-signature") || []).map((val) =>
    parseDkimSignature(val, warnings)
  );

  // Received-SPF
  const receivedSpf = (byName.get("received-spf") || []).map((val) =>
    parseReceivedSpf(val, warnings)
  );

  // ARC headers
  const arcInfo = parseArc(
    byName.get("arc-seal") || [],
    byName.get("arc-message-signature") || [],
    byName.get("arc-authentication-results") || [],
    warnings
  );

  // X-Forefront-Antispam-Report
  const forefrontVals = byName.get("x-forefront-antispam-report") || [];
  const forefrontInfo =
    forefrontVals.length > 0 ? parseForefrontReport(forefrontVals[0]) : null;

  // Received chain
  const receivedHops = parseReceived(byName.get("received") || [], warnings);

  // Alignment & DMARC verdict
  const { alignment, dmarc } = evaluateAlignmentAndDmarc({
    fromDomain: fromInfo.domain,
    authResults,
    dkimSignatures,
    receivedSpf,
    warnings,
  });

  return {
    from: fromInfo,
    reply_to: replyToInfo,
    return_path: returnPathInfo,
    to: toInfo,
    subject: subjectInfo,
    date: dateInfo,
    message_id: messageId,
    auth_results: authResults,
    dkim_signatures: dkimSignatures,
    received_spf: receivedSpf,
    arc: arcInfo,
    x_forefront_antispam_report: forefrontInfo,
    received: receivedHops,
    alignment,
    dmarc,
    warnings,
  };
}

// ---------------------------------------------------------------------------
// HTML rendering (8 inline sections, strict HTML escaping for all values)
// ---------------------------------------------------------------------------

/**
 * Strictly HTML-escape any untrusted value (&, <, >, ", ').
 */
export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

function verdictState(result) {
  const norm = String(result || "").trim().toLowerCase();
  if (norm === "pass") return "pass";
  if (norm === "fail") return "fail";
  return "unknown";
}

function statusState(result) {
  const norm = String(result || "").trim().toLowerCase();
  if (norm === "pass" || norm === "bestguesspass") return "pass";
  if (norm === "fail" || norm === "hardfail" || norm === "permerror") {
    return "fail";
  }
  if (
    norm === "softfail" ||
    norm === "neutral" ||
    norm === "temperror" ||
    norm === "policy"
  ) {
    return "warn";
  }
  return "unknown";
}

function formatDelay(delaySeconds) {
  if (delaySeconds === null || delaySeconds === undefined) return "origin";
  const sign = delaySeconds < 0 ? "-" : "+";
  const absSec = Math.abs(Number(delaySeconds));
  if (absSec === 0) return "0s";
  if (absSec < 60) {
    const clean = Number(absSec.toFixed(3));
    return `${sign}${clean}s`;
  }
  const totalSec = Math.round(absSec);
  const minutesTotal = Math.floor(totalSec / 60);
  const secs = totalSec % 60;
  if (minutesTotal < 60) {
    return `${sign}${minutesTotal}m ${secs}s`;
  }
  const hours = Math.floor(minutesTotal / 60);
  const minutes = minutesTotal % 60;
  return `${sign}${hours}h ${minutes}m ${secs}s`;
}

function formatDkimTimestamp(tVal) {
  if (!tVal) return "—";
  const stripped = String(tVal).trim();
  if (isDigits(stripped)) {
    const epoch = Number(stripped);
    const dt = new Date(epoch * 1000);
    if (!Number.isNaN(dt.getTime())) {
      const y = String(dt.getUTCFullYear()).padStart(4, "0");
      const m = pad2(dt.getUTCMonth() + 1);
      const d = pad2(dt.getUTCDate());
      const hh = pad2(dt.getUTCHours());
      const mm = pad2(dt.getUTCMinutes());
      const ss = pad2(dt.getUTCSeconds());
      return `${y}-${m}-${d} ${hh}:${mm}:${ss} UTC (t=${stripped})`;
    }
  }
  return stripped;
}

function extractMsgIdDomain(messageId) {
  if (!messageId || !String(messageId).includes("@")) return null;
  return normalizeDomain(messageId);
}

/**
 * Build one plain-English sentence explaining the DMARC verdict.
 * Returns unescaped plain text; caller MUST escape with escapeHtml().
 */
function explainVerdict(parsed) {
  const dmarc = parsed.dmarc || {};
  const alignment = parsed.alignment || {};
  const fromDom = alignment.from_domain;
  const fromLabel = fromDom || "the From domain";
  const dmarcRes = String(dmarc.result || "unknown").trim().toLowerCase();
  const reason = dmarc.reason || (dmarc.computed && dmarc.computed.reason) || null;

  const spf = alignment.spf || {};
  const dkim = alignment.dkim || {};
  const spfRes = String(spf.result || "unknown").trim().toLowerCase();
  const spfDom = spf.domain;
  const spfAligned = Boolean(spf.aligned);
  const spfPasses = Boolean(spf.passes_dmarc);

  const dkimEntries = dkim.entries || [];
  const dkimRes = String(dkim.result || "unknown").trim().toLowerCase();
  const dkimAligned = Boolean(dkim.aligned);
  const dkimPasses = Boolean(dkim.passes_dmarc);

  const arcPresent = Boolean(parsed.arc && parsed.arc.present);

  const passingAlignedDkim = dkimEntries.filter((e) => e.passes_dmarc);
  const passingDkim = dkimEntries.filter((e) => e.result === "pass");

  if (dmarc.disagreement) {
    const compRes = (dmarc.computed && dmarc.computed.result) || "unknown";
    const detail = reason ? ` (${reason})` : "";
    return (
      `The receiving server reported DMARC ${dmarcRes}${detail} for ${fromLabel}, ` +
      `which disagrees with the computed DMARC ${compRes} from the SPF and DKIM results — ` +
      `review the disagreement warning below.`
    );
  }

  if (dmarcRes === "pass") {
    const dkimPassDom =
      passingAlignedDkim.length > 0 ? passingAlignedDkim[0].domain : null;
    if (spfPasses && dkimPasses) {
      return (
        `Both SPF (${spfDom || fromLabel}) and DKIM (${dkimPassDom || fromLabel}) ` +
        `passed and aligned with ${fromLabel}, authenticating the message.`
      );
    }
    if (spfPasses) {
      return (
        `SPF passed for ${spfDom || fromLabel}, which aligns with the From domain ` +
        `${fromLabel}, so DMARC passed.`
      );
    }
    if (dkimPasses) {
      return (
        `DKIM passed for ${dkimPassDom || fromLabel}, which aligns with the From domain ` +
        `${fromLabel}, so DMARC passed.`
      );
    }
    return `The receiving server reported DMARC pass for ${fromLabel}, authenticating the message.`;
  }

  if (dmarcRes === "fail") {
    const clauses = [];
    const reasonTokens = new Set(
      reason
        ? String(reason)
            .split(",")
            .map((p) => p.trim())
        : []
    );

    // Describe SPF contribution
    if (
      reasonTokens.has("SPF not aligned") ||
      (spfRes === "pass" && !spfAligned)
    ) {
      if (spf.mode === "strict" && spf.relaxed_aligned) {
        clauses.push(
          `SPF passed for ${spfDom || "an unknown domain"}, which does not strictly match the From domain`
        );
      } else {
        clauses.push(
          `SPF passed for ${spfDom || "an unknown domain"}, which is not the From domain`
        );
      }
    } else if (
      reasonTokens.has("SPF failed") ||
      (spfRes !== "unknown" && spfRes !== "pass")
    ) {
      const verb = spfRes === "fail" ? "failed" : `returned ${spfRes}`;
      if (spfDom) {
        clauses.push(`SPF ${verb} for ${spfDom}`);
      } else {
        clauses.push(`SPF ${verb}`);
      }
    }

    // Describe DKIM contribution
    if (
      reasonTokens.has("DKIM not aligned") ||
      (dkimRes === "pass" && !dkimAligned)
    ) {
      const unalignedDom =
        passingDkim.length > 0
          ? passingDkim[0].domain
          : dkimEntries.length > 0
          ? dkimEntries[0].domain
          : null;
      if (dkim.mode === "strict" && dkim.relaxed_aligned) {
        clauses.push(
          `DKIM passed for ${unalignedDom || "an unknown domain"}, which does not strictly match the From domain`
        );
      } else {
        clauses.push(
          `DKIM passed for ${unalignedDom || "an unknown domain"}, which is not the From domain`
        );
      }
    } else if (
      reasonTokens.has("DKIM failed") ||
      (dkimRes !== "unknown" && dkimRes !== "pass")
    ) {
      const dkimDom = dkimEntries.length > 0 ? dkimEntries[0].domain : null;
      const verb = dkimRes === "fail" ? "failed" : `returned ${dkimRes}`;
      if (dkimDom) {
        clauses.push(`DKIM ${verb} for ${dkimDom}`);
      } else {
        clauses.push(`DKIM ${verb}`);
      }
    }

    const arcSuffix = arcPresent
      ? " (ARC headers are present, indicating the message was likely forwarded)"
      : "";
    if (clauses.length > 0) {
      return `${clauses.join(" and ")} — the message is not authenticated as ${fromLabel}${arcSuffix}.`;
    }
    if (reason) {
      return (
        `DMARC failed for ${fromLabel} because the receiver reported ${reason} — ` +
        `the message is not authenticated as ${fromLabel}${arcSuffix}.`
      );
    }
    return (
      `Neither SPF nor DKIM passed with alignment for ${fromLabel} — ` +
      `the message is not authenticated as ${fromLabel}${arcSuffix}.`
    );
  }

  if (dmarcRes === "unknown") {
    const authResults = parsed.auth_results || [];
    const dkimSigs = parsed.dkim_signatures || [];
    if (authResults.length === 0) {
      if (dkimSigs.length > 0) {
        return (
          `No Authentication-Results header is present to verify SPF or DKIM, ` +
          `so DMARC cannot be determined for ${fromLabel} ` +
          `(although ${dkimSigs.length} unverified DKIM signature(s) were found).`
        );
      }
      return (
        `No Authentication-Results header is present, so DMARC authentication ` +
        `for ${fromLabel} cannot be determined.`
      );
    }
    return (
      `Authentication-Results did not include SPF, DKIM, or DMARC results, ` +
      `so DMARC authentication for ${fromLabel} cannot be determined.`
    );
  }

  const detail = reason ? ` (${reason})` : "";
  return (
    `The receiving server reported DMARC ${dmarcRes}${detail} for ${fromLabel}, ` +
    `so the message did not pass DMARC authentication.`
  );
}

function renderAddressHtml(addrInfo) {
  if (
    !addrInfo ||
    (addrInfo.address === null && addrInfo.raw === null) ||
    (addrInfo.address === undefined && addrInfo.raw === undefined)
  ) {
    return '<span class="muted">—</span>';
  }

  const disp = addrInfo.display_name;
  const rawDisp = addrInfo.raw_display_name;
  const addr = addrInfo.address;
  const dom = addrInfo.domain;
  const rawVal = addrInfo.raw;

  const parts = [];
  if (disp) {
    parts.push(`<span class="addr-display">${escapeHtml(disp)}</span>`);
  }
  if (addr === "") {
    parts.push('<span class="mono">&lt;&gt;</span>');
  } else if (addr) {
    parts.push(`<span class="mono">&lt;${escapeHtml(addr)}&gt;</span>`);
  } else if (rawVal) {
    parts.push(`<span class="mono">${escapeHtml(rawVal)}</span>`);
  }

  if (dom) {
    parts.push(`<span class="chip chip-muted">${escapeHtml(dom)}</span>`);
  }
  if (disp && rawDisp && disp !== rawDisp) {
    parts.push('<span class="chip chip-muted">RFC 2047 decoded</span>');
  }

  return parts.join(" ");
}

/**
 * Render parsed email header analysis as an inline HTML report string
 * (same 8 sections as Milestone 2: verdict, why, alignment, message summary,
 * Authentication-Results, DKIM signatures, Received chain, warnings).
 *
 * Every interpolated value is strictly HTML-escaped.
 */
export function renderReport(parsed) {
  const data = parsed || {};
  const dmarc = data.dmarc || {};
  const alignment = data.alignment || {};
  const fromInfo = data.from || {};
  const fromDom = alignment.from_domain || fromInfo.domain || null;
  const fromOrg = alignment.from_org_domain || null;

  const dmarcResultRaw = dmarc.result || "unknown";
  const vState = verdictState(dmarcResultRaw);
  const dmarcProvenance = dmarc.provenance || "unknown";
  const policy = dmarc.policy || {};

  const sections = [];

  // --- 1. Verdict banner (DECIDES VERDICT) ---
  const policyKeys = ["p", "sp", "dis"];
  for (const extraK of Object.keys(policy).sort()) {
    if (!policyKeys.includes(extraK) && policy[extraK] !== null && policy[extraK] !== undefined) {
      policyKeys.push(extraK);
    }
  }
  const policyChips = policyKeys
    .map((k) => {
      const v = policy[k] !== null && policy[k] !== undefined ? policy[k] : "—";
      return `<span class="chip">${escapeHtml(k)}=${escapeHtml(v)}</span>`;
    })
    .join("");

  const fromDomainDisplay = fromDom ? escapeHtml(fromDom) : "(none)";
  sections.push(
    `<section class="card verdict-banner decides-verdict verdict-${vState}" aria-label="DMARC Verdict">\n` +
      `  <div class="verdict-top">\n` +
      `    <span class="decides-marker">Decides verdict</span>\n` +
      `    <span class="chip-provenance">provenance: ${escapeHtml(dmarcProvenance)}</span>\n` +
      `  </div>\n` +
      `  <h2 class="verdict-heading">` +
      `<span class="verdict-label">DMARC</span> ` +
      `<span class="verdict-word">${escapeHtml(dmarcResultRaw)}</span>` +
      `</h2>\n` +
      `  <div class="verdict-meta">\n` +
      `    <div class="meta-item">` +
      `<span class="meta-label">From domain:</span> ` +
      `<span class="chip chip-domain-strong">${fromDomainDisplay}</span>` +
      `</div>\n` +
      `    <div class="meta-item">` +
      `<span class="meta-label">Policy:</span> ` +
      `<span class="policy-group">${policyChips}</span>` +
      `</div>\n` +
      `  </div>\n` +
      `</section>`
  );

  // --- 2. Why ---
  const whySentence = explainVerdict(data);
  sections.push(
    `<section class="card why-section" aria-label="Why">\n` +
      `  <div class="section-header">\n` +
      `    <h2>Why</h2>\n` +
      `  </div>\n` +
      `  <p class="why-text">${escapeHtml(whySentence)}</p>\n` +
      `</section>`
  );

  // --- 3. Alignment table (DECIDES VERDICT) ---
  const spf = alignment.spf || {};
  const dkim = alignment.dkim || {};
  const alignmentRows = [];

  function buildAlignmentRow({
    mechKey,
    mechLabel,
    mode,
    resultVal,
    domVal,
    alignedFlag,
    strictFlag,
    provenanceVal,
    selector = null,
  }) {
    const stCls = statusState(resultVal);
    const isMismatch = Boolean(domVal && !alignedFlag);
    const domTdCls = isMismatch ? ' class="cell-mismatch"' : "";

    let domHtml;
    if (domVal) {
      domHtml = `<span class="chip">${escapeHtml(domVal)}</span>`;
      if (isMismatch) {
        domHtml += '<span class="mismatch-tag">Mismatch</span>';
      }
    } else {
      domHtml = '<span class="muted">(none)</span>';
    }

    let alignedHtml;
    if (alignedFlag) {
      const alignDetail = strictFlag ? "strict" : "relaxed";
      alignedHtml = `<span class="status-badge status-pass">Aligned (${escapeHtml(alignDetail)})</span>`;
    } else if (isMismatch) {
      alignedHtml = `<span class="status-badge status-fail">Mismatch (${escapeHtml(mode)})</span>`;
    } else {
      alignedHtml = `<span class="status-badge status-unknown">Not aligned (${escapeHtml(mode)})</span>`;
    }

    let mechSub = `mode: ${mode}`;
    if (selector) {
      mechSub += ` · s=${selector}`;
    }

    return (
      `      <tr class="mechanism-row" data-mechanism="${escapeHtml(mechKey)}">\n` +
      `        <td><strong>${escapeHtml(mechLabel)}</strong><span class="sub-note">${escapeHtml(mechSub)}</span></td>\n` +
      `        <td><span class="status-badge status-${stCls}">${escapeHtml(resultVal)}</span></td>\n` +
      `        <td${domTdCls}>${domHtml}</td>\n` +
      `        <td>${alignedHtml}</td>\n` +
      `        <td><span class="chip-provenance">${escapeHtml(provenanceVal)}</span></td>\n` +
      `      </tr>`
    );
  }

  alignmentRows.push(
    buildAlignmentRow({
      mechKey: "spf",
      mechLabel: "SPF",
      mode: spf.mode || "relaxed",
      resultVal: spf.result || "unknown",
      domVal: spf.domain || null,
      alignedFlag: Boolean(spf.aligned),
      strictFlag: Boolean(spf.strict_aligned),
      provenanceVal: spf.provenance || "unknown",
    })
  );

  const dkimEntries = dkim.entries || [];
  if (dkimEntries.length > 0) {
    for (const entry of dkimEntries) {
      alignmentRows.push(
        buildAlignmentRow({
          mechKey: "dkim",
          mechLabel: "DKIM",
          mode: entry.mode || dkim.mode || "relaxed",
          resultVal: entry.result || "unknown",
          domVal: entry.domain || null,
          alignedFlag: Boolean(entry.aligned),
          strictFlag: Boolean(entry.strict_aligned),
          provenanceVal: entry.provenance || dkim.provenance || "unknown",
          selector: entry.selector || null,
        })
      );
    }
  } else {
    alignmentRows.push(
      buildAlignmentRow({
        mechKey: "dkim",
        mechLabel: "DKIM",
        mode: dkim.mode || "relaxed",
        resultVal: dkim.result || "unknown",
        domVal: null,
        alignedFlag: Boolean(dkim.aligned),
        strictFlag: Boolean(dkim.strict_aligned),
        provenanceVal: dkim.provenance || "unknown",
      })
    );
  }

  const orgNote =
    fromOrg && fromOrg !== fromDom
      ? ` <span class="chip chip-muted">org: ${escapeHtml(fromOrg)}</span>`
      : "";

  sections.push(
    `<section class="card alignment-section decides-verdict" aria-label="Alignment">\n` +
      `  <div class="section-header">\n` +
      `    <div class="section-title-group">\n` +
      `      <h2>Alignment</h2>\n` +
      `      <span class="decides-marker">Decides verdict</span>\n` +
      `    </div>\n` +
      `    <div class="from-compare">From domain: <span class="chip chip-domain-strong">${fromDomainDisplay}</span>${orgNote}</div>\n` +
      `  </div>\n` +
      `  <div class="table-wrap">\n` +
      `    <table>\n` +
      `      <thead>\n` +
      `        <tr>\n` +
      `          <th>Mechanism</th>\n` +
      `          <th>Result</th>\n` +
      `          <th>Domain</th>\n` +
      `          <th>Aligned?</th>\n` +
      `          <th>Provenance</th>\n` +
      `        </tr>\n` +
      `      </thead>\n` +
      `      <tbody>\n` +
      alignmentRows.join("\n") +
      `\n      </tbody>\n` +
      `    </table>\n` +
      `  </div>\n` +
      `</section>`
  );

  // --- 4. Message summary ---
  const toList = data.to || [];
  let toHtml;
  if (toList.length > 0) {
    const toItems = toList
      .map((item) => `<div class="addr-item">${renderAddressHtml(item)}</div>`)
      .join("");
    toHtml = `<div class="addr-list">${toItems}</div>`;
  } else {
    toHtml = '<span class="muted">—</span>';
  }

  const subj = data.subject;
  let subjHtml;
  if (subj && subj.decoded !== null && subj.decoded !== undefined) {
    subjHtml = `<span>${escapeHtml(subj.decoded)}</span>`;
    if (subj.raw && subj.raw !== subj.decoded) {
      subjHtml += '<span class="chip chip-muted">RFC 2047 decoded</span>';
    }
  } else {
    subjHtml = '<span class="muted">—</span>';
  }

  const dateInfo = data.date;
  let dateHtml;
  if (dateInfo && dateInfo.raw) {
    dateHtml = `<span class="mono">${escapeHtml(dateInfo.raw)}</span>`;
    if (dateInfo.iso) {
      dateHtml += `<span class="chip chip-muted">${escapeHtml(dateInfo.iso)}</span>`;
    }
  } else {
    dateHtml = '<span class="muted">—</span>';
  }

  const msgId = data.message_id;
  let msgIdHtml;
  if (msgId) {
    const msgIdDom = extractMsgIdDomain(msgId);
    msgIdHtml = `<span class="mono">${escapeHtml(msgId)}</span>`;
    if (msgIdDom) {
      msgIdHtml += `<span class="chip chip-muted">${escapeHtml(msgIdDom)}</span>`;
    }
  } else {
    msgIdHtml = '<span class="muted">—</span>';
  }

  sections.push(
    `<section class="card summary-section" aria-label="Message Summary">\n` +
      `  <div class="section-header">\n` +
      `    <h2>Message summary</h2>\n` +
      `  </div>\n` +
      `  <dl class="summary-grid">\n` +
      `    <dt>From</dt><dd>${renderAddressHtml(fromInfo)}</dd>\n` +
      `    <dt>Reply-To</dt><dd>${renderAddressHtml(data.reply_to)}</dd>\n` +
      `    <dt>Return-Path</dt><dd>${renderAddressHtml(data.return_path)}</dd>\n` +
      `    <dt>To</dt><dd>${toHtml}</dd>\n` +
      `    <dt>Subject</dt><dd>${subjHtml}</dd>\n` +
      `    <dt>Date</dt><dd>${dateHtml}</dd>\n` +
      `    <dt>Message-ID</dt><dd>${msgIdHtml}</dd>\n` +
      `  </dl>\n` +
      `</section>`
  );

  // --- 5. Authentication-Results ---
  const authResults = data.auth_results || [];
  const arBlocks = [];
  if (authResults.length === 0) {
    arBlocks.push(
      '  <p class="empty-state">No Authentication-Results headers present.</p>'
    );
  } else {
    for (const ar of authResults) {
      const idxNum = Number(ar.index || 0) + 1;
      const isAuth = Boolean(ar.is_authoritative);
      const instCls = isAuth
        ? "ar-instance ar-instance-authoritative"
        : "ar-instance";
      const roleCls = isAuth
        ? "role-badge role-authoritative"
        : "role-badge role-secondary";
      const roleText = isAuth ? "authoritative" : "non-authoritative";
      const authserv = ar.authserv_id || "(unknown authserv-id)";

      const resRows = [];
      for (const res of ar.results || []) {
        const meth = res.method || "unknown";
        const resVal = res.result || "unknown";
        const stCls = statusState(resVal);
        const resDom = res.domain;
        const domCell = resDom
          ? `<span class="chip chip-muted">${escapeHtml(resDom)}</span>`
          : '<span class="muted">—</span>';

        const propChips = [];
        const resProps = res.properties || {};
        for (const [pk, pv] of Object.entries(resProps)) {
          propChips.push(
            `<span class="prop-chip">${escapeHtml(pk)}=${escapeHtml(pv)}</span>`
          );
        }
        const resPolicy = res.policy || {};
        for (const [polK, polV] of Object.entries(resPolicy)) {
          if (!Object.prototype.hasOwnProperty.call(resProps, `policy.${polK}`)) {
            propChips.push(
              `<span class="prop-chip">${escapeHtml(polK)}=${escapeHtml(polV)}</span>`
            );
          }
        }

        const detailsParts = [];
        if (propChips.length > 0) {
          detailsParts.push(`<div class="props-list">${propChips.join("")}</div>`);
        }
        if (res.reason) {
          detailsParts.push(
            `<span class="sub-note">${escapeHtml(res.reason)}</span>`
          );
        }
        const detailsCell =
          detailsParts.length > 0
            ? detailsParts.join("")
            : '<span class="muted">—</span>';

        resRows.push(
          `          <tr>\n` +
            `            <td class="mono"><strong>${escapeHtml(meth)}</strong></td>\n` +
            `            <td><span class="status-badge status-${stCls}">${escapeHtml(resVal)}</span></td>\n` +
            `            <td>${domCell}</td>\n` +
            `            <td>${detailsCell}</td>\n` +
            `          </tr>`
        );
      }

      const tableHtml =
        resRows.length > 0
          ? `    <div class="table-wrap">\n` +
            `      <table>\n` +
            `        <thead>\n` +
            `          <tr>\n` +
            `            <th>Method</th>\n` +
            `            <th>Result</th>\n` +
            `            <th>Domain</th>\n` +
            `            <th>Properties &amp; Details</th>\n` +
            `          </tr>\n` +
            `        </thead>\n` +
            `        <tbody>\n` +
            resRows.join("\n") +
            `\n        </tbody>\n` +
            `      </table>\n` +
            `    </div>`
          : '    <p class="empty-state">No method results reported.</p>';

      arBlocks.push(
        `  <div class="${instCls}">\n` +
          `    <div class="ar-instance-header">\n` +
          `      <div class="ar-instance-title">\n` +
          `        <span class="count-chip">#${idxNum}</span>\n` +
          `        <h3 class="mono">${escapeHtml(authserv)}</h3>\n` +
          `      </div>\n` +
          `      <span class="${roleCls}">${roleText}</span>\n` +
          `    </div>\n` +
          `${tableHtml}\n` +
          `  </div>`
      );
    }
  }

  // Supplementary authentication headers (only when present)
  const supplements = [];
  const receivedSpf = data.received_spf || [];
  if (receivedSpf.length > 0) {
    const rspfItems = receivedSpf.map((rspf) => {
      const rRes = rspf.result || "unknown";
      const stCls = statusState(rRes);
      const domChip = rspf.domain
        ? ` <span class="chip chip-muted">${escapeHtml(rspf.domain)}</span>`
        : "";
      const disagreeTag = rspf.disagrees_with_auth_results
        ? ' <span class="mismatch-tag">Disagrees with Auth-Results</span>'
        : "";
      return (
        `      <div class="addr-item">` +
        `<span class="status-badge status-${stCls}">${escapeHtml(rRes)}</span>` +
        `${domChip}${disagreeTag}` +
        `</div>`
      );
    });
    supplements.push(
      `  <div class="ar-supplement">\n` +
        `    <div class="ar-supplement-title">Received-SPF</div>\n` +
        `    <div class="addr-list">\n` +
        rspfItems.join("\n") +
        `\n    </div>\n` +
        `  </div>`
    );
  }

  const arc = data.arc || {};
  if (arc.present) {
    const arcChips =
      `<span class="chip">instances=${escapeHtml(arc.instance_count ?? 0)}</span>` +
      `<span class="chip chip-muted">seals=${escapeHtml(arc.seal_count ?? 0)}</span>` +
      `<span class="chip chip-muted">msg-sigs=${escapeHtml(arc.message_signature_count ?? 0)}</span>` +
      `<span class="chip chip-muted">auth-results=${escapeHtml(arc.auth_results_count ?? 0)}</span>`;
    supplements.push(
      `  <div class="ar-supplement">\n` +
        `    <div class="ar-supplement-title">ARC (Authenticated Received Chain)</div>\n` +
        `    <div class="props-list">${arcChips}</div>\n` +
        `  </div>`
    );
  }

  const forefront = data.x_forefront_antispam_report;
  if (forefront) {
    const ffChips = [];
    if (forefront.scl !== null && forefront.scl !== undefined) {
      let sclText = `SCL=${forefront.scl}`;
      if (forefront.scl_meaning) sclText += ` (${forefront.scl_meaning})`;
      ffChips.push(`<span class="chip">${escapeHtml(sclText)}</span>`);
    }
    if (forefront.bcl !== null && forefront.bcl !== undefined) {
      ffChips.push(`<span class="chip">BCL=${escapeHtml(forefront.bcl)}</span>`);
    }
    if (forefront.cat) {
      let catText = `CAT=${forefront.cat}`;
      if (forefront.cat_meaning) catText += ` (${forefront.cat_meaning})`;
      ffChips.push(`<span class="chip">${escapeHtml(catText)}</span>`);
    }
    if (ffChips.length > 0) {
      supplements.push(
        `  <div class="ar-supplement">\n` +
          `    <div class="ar-supplement-title">X-Forefront-Antispam-Report</div>\n` +
          `    <div class="props-list">${ffChips.join("")}</div>\n` +
          `  </div>`
      );
    }
  }

  sections.push(
    `<section class="card auth-results-section" aria-label="Authentication-Results">\n` +
      `  <div class="section-header">\n` +
      `    <div class="section-title-group">\n` +
      `      <h2>Authentication-Results</h2>\n` +
      `      <span class="count-chip">${authResults.length}</span>\n` +
      `    </div>\n` +
      `  </div>\n` +
      arBlocks.join("\n") +
      (supplements.length > 0 ? "\n" + supplements.join("\n") : "") +
      `\n</section>`
  );

  // --- 6. DKIM signatures ---
  const dkimSigs = data.dkim_signatures || [];
  let dkimBody;
  if (dkimSigs.length === 0) {
    dkimBody = '  <p class="empty-state">No DKIM-Signature headers present.</p>';
  } else {
    const sigRows = dkimSigs.map((sig) => {
      const domCell = sig.d
        ? `<span class="chip">${escapeHtml(sig.d)}</span>`
        : '<span class="muted">—</span>';
      const selCell = escapeHtml(sig.s || "—");
      const algCell = escapeHtml(sig.a || "—");
      const canonCell = escapeHtml(sig.c || "—");
      const hCell = escapeHtml(sig.h || "—");
      const tCell = escapeHtml(formatDkimTimestamp(sig.t));
      return (
        `      <tr>\n` +
        `        <td>${domCell}</td>\n` +
        `        <td class="mono">${selCell}</td>\n` +
        `        <td class="mono">${algCell}</td>\n` +
        `        <td class="mono">${canonCell}</td>\n` +
        `        <td class="dkim-h-list">${hCell}</td>\n` +
        `        <td class="mono">${tCell}</td>\n` +
        `      </tr>`
      );
    });
    dkimBody =
      `  <div class="table-wrap">\n` +
      `    <table>\n` +
      `      <thead>\n` +
      `        <tr>\n` +
      `          <th>Domain</th>\n` +
      `          <th>Selector</th>\n` +
      `          <th>Algorithm</th>\n` +
      `          <th>Canonicalization</th>\n` +
      `          <th>Headers covered (h=)</th>\n` +
      `          <th>Timestamp</th>\n` +
      `        </tr>\n` +
      `      </thead>\n` +
      `      <tbody>\n` +
      sigRows.join("\n") +
      `\n      </tbody>\n` +
      `    </table>\n` +
      `  </div>`;
  }

  sections.push(
    `<section class="card dkim-section" aria-label="DKIM Signatures">\n` +
      `  <div class="section-header">\n` +
      `    <div class="section-title-group">\n` +
      `      <h2>DKIM signatures</h2>\n` +
      `      <span class="count-chip">${dkimSigs.length}</span>\n` +
      `    </div>\n` +
      `  </div>\n` +
      `${dkimBody}\n` +
      `</section>`
  );

  // --- 7. Received chain ---
  const received = data.received || [];
  let recvBody;
  if (received.length === 0) {
    recvBody = '  <p class="empty-state">No Received headers present.</p>';
  } else {
    const positiveDelays = received
      .map((h) => h.delay_seconds)
      .filter((d) => d !== null && d !== undefined && d > 0);
    const maxDelay =
      positiveDelays.length > 0 ? Math.max(...positiveDelays) : null;

    const hopRows = received.map((hop) => {
      const hopNum = Number(hop.index || 0) + 1;
      const fromHost = hop.from_host || "—";
      const byHost = hop.by_host || "—";
      const ipNote = hop.ip
        ? `<span class="sub-note mono">[${escapeHtml(hop.ip)}]</span>`
        : "";
      const protoNote = hop.with_protocol
        ? `<span class="sub-note mono">with ${escapeHtml(hop.with_protocol)}</span>`
        : "";
      const dateRaw = hop.date_raw || "—";
      const dateIsoNote = hop.date_iso
        ? `<span class="sub-note mono">${escapeHtml(hop.date_iso)}</span>`
        : "";
      const delay = hop.delay_seconds;
      const isLargest =
        maxDelay !== null &&
        delay !== null &&
        delay !== undefined &&
        delay === maxDelay;
      const trCls = isLargest ? ' class="hop-largest-delay"' : "";
      const delayText = escapeHtml(formatDelay(delay));
      const largestBadge = isLargest
        ? '<span class="delay-largest-badge">Largest delay</span>'
        : "";

      return (
        `      <tr${trCls}>\n` +
        `        <td class="mono">#${hopNum}</td>\n` +
        `        <td><span class="mono">${escapeHtml(fromHost)}</span>${ipNote}</td>\n` +
        `        <td><span class="mono">${escapeHtml(byHost)}</span>${protoNote}</td>\n` +
        `        <td><span class="mono">${escapeHtml(dateRaw)}</span>${dateIsoNote}</td>\n` +
        `        <td><span class="mono">${delayText}</span>${largestBadge}</td>\n` +
        `      </tr>`
      );
    });

    recvBody =
      `  <div class="table-wrap">\n` +
      `    <table>\n` +
      `      <thead>\n` +
      `        <tr>\n` +
      `          <th>Hop</th>\n` +
      `          <th>From</th>\n` +
      `          <th>By</th>\n` +
      `          <th>Timestamp</th>\n` +
      `          <th>Delay</th>\n` +
      `        </tr>\n` +
      `      </thead>\n` +
      `      <tbody>\n` +
      hopRows.join("\n") +
      `\n      </tbody>\n` +
      `    </table>\n` +
      `  </div>`;
  }

  const hopUnit = received.length === 1 ? "hop" : "hops";
  sections.push(
    `<section class="card received-section" aria-label="Received Chain">\n` +
      `  <div class="section-header">\n` +
      `    <div class="section-title-group">\n` +
      `      <h2>Received chain</h2>\n` +
      `      <span class="count-chip">${received.length} ${hopUnit}</span>\n` +
      `    </div>\n` +
      `    <span class="muted">Reverse chronological (newest first)</span>\n` +
      `  </div>\n` +
      `${recvBody}\n` +
      `</section>`
  );

  // --- 8. Warnings (ONLY if non-empty or disagreement) ---
  const warnings = data.warnings || [];
  const hasDisagreement = Boolean(dmarc.disagreement);
  if (warnings.length > 0 || hasDisagreement) {
    const warnInner = [];
    const disagreementDetail = dmarc.disagreement_detail;
    if (hasDisagreement) {
      const reportedRes = (dmarc.reported && dmarc.reported.result) || "unknown";
      const computedRes = (dmarc.computed && dmarc.computed.result) || "unknown";
      const detailMsg =
        disagreementDetail ||
        `Reported DMARC (${reportedRes}) disagrees with computed DMARC (${computedRes}).`;
      warnInner.push(
        `  <div class="callout-disagreement" role="alert">\n` +
          `    <p class="callout-title">Reported vs. Computed DMARC Disagreement</p>\n` +
          `    <p class="callout-body">${escapeHtml(detailMsg)}</p>\n` +
          `  </div>`
      );
    }

    const remainingWarnings = warnings.filter(
      (w) =>
        !(
          hasDisagreement &&
          disagreementDetail &&
          w === `DMARC disagreement: ${disagreementDetail}`
        )
    );
    if (remainingWarnings.length > 0) {
      const liItems = remainingWarnings
        .map((w) => `    <li>${escapeHtml(w)}</li>`)
        .join("\n");
      warnInner.push(`  <ul class="warnings-list">\n${liItems}\n  </ul>`);
    }

    const warnCount = warnings.length > 0 ? warnings.length : 1;
    sections.push(
      `<section class="card warnings-section" aria-label="Warnings">\n` +
        `  <div class="section-header">\n` +
        `    <div class="section-title-group">\n` +
        `      <h2>Warnings</h2>\n` +
        `      <span class="count-chip">${warnCount}</span>\n` +
        `    </div>\n` +
        `  </div>\n` +
        warnInner.join("\n") +
        `\n</section>`
    );
  }

  return `<div class="dmarc-report">\n${sections.join("\n")}\n</div>\n`;
}
