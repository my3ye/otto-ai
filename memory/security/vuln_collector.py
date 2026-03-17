"""
Vulnerability Intelligence Collector
Fetches from: NVD/CVE API, Rekt.news, DeFiHackLabs, MITRE ATLAS
Auto-maps vulnerabilities to affected Otto/MY3YE systems.
"""
import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
import aiohttp
import asyncpg

# Database config
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "memory")
DB_USER = os.getenv("POSTGRES_USER", "otto")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "")

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFIHACKLABS_URL = "https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/main/README.md"
REKT_NEWS_LEADERBOARD = "https://raw.githubusercontent.com/decurity/rekt-api/main/data/rekt-news.json"
# Fallback rekt source
REKT_LEADERBOARD_URL = "https://rekt.news/leaderboard/"

SEVERITY_MAP = {
    (9.0, 10.0): "CRITICAL",
    (7.0, 8.9): "HIGH",
    (4.0, 6.9): "MEDIUM",
    (0.1, 3.9): "LOW",
    (0.0, 0.0): "INFO",
}

# Verticals for NVD keyword-based classification
NVD_VERTICAL_KEYWORDS = {
    "blockchain": ["solidity", "ethereum", "smart contract", "evm", "defi", "token", "web3", "blockchain",
                   "solana", "rust anchor", "chainlink", "openzeppelin", "uniswap"],
    "ai": ["llm", "language model", "tensorflow", "pytorch", "machine learning", "artificial intelligence",
            "neural network", "hugging face", "openai", "anthropic", "prompt", "inference"],
    "vm_infra": ["linux", "debian", "ubuntu", "docker", "container", "kubernetes", "gcp", "aws",
                  "systemd", "kernel", "privilege escalation", "cve", "vm", "hypervisor"],
    "web": ["nginx", "apache", "http", "https", "xss", "csrf", "sqli", "injection", "nextjs", "react",
             "fastapi", "flask", "django", "express", "node", "npm", "jwt", "oauth", "websocket"],
    "mobile": ["android", "ios", "react native", "expo", "mobile", "apk", "swift", "objective-c"],
    "network": ["tcp", "udp", "dns", "bgp", "ddos", "firewall", "vpn", "tls", "ssl", "ssh",
                 "p2p", "libp2p", "network protocol"],
    "robotics": ["ros", "robot", "firmware", "iot", "embedded", "uart", "can bus", "hardware", "plc",
                  "scada", "sensor", "actuator"],
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("vuln_collector")


def make_hash(source: str, external_id: str) -> str:
    return hashlib.sha256(f"{source}:{external_id}".encode()).hexdigest()


def classify_vertical(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for vertical, keywords in NVD_VERTICAL_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[vertical] = score
    if not scores:
        return "vm_infra"  # Default for generic CVEs
    return max(scores, key=scores.get)


def cvss_to_severity(score: Optional[float]) -> str:
    if score is None:
        return "MEDIUM"
    for (low, high), sev in SEVERITY_MAP.items():
        if low <= score <= high:
            return sev
    return "LOW"


async def get_system_map(conn) -> list[dict]:
    """Fetch Otto system map from DB."""
    rows = await conn.fetch("SELECT * FROM vuln_system_map")
    return [dict(r) for r in rows]


def map_to_otto_systems(text: str, system_map: list[dict]) -> list[str]:
    """Map vulnerability text to affected Otto systems via keyword matching."""
    text_lower = text.lower()
    affected = []
    for sys in system_map:
        for kw in (sys["keywords"] or []):
            if kw.lower() in text_lower:
                affected.append(sys["otto_system"])
                break
        else:
            for tech in (sys["tech_stack"] or []):
                if tech.lower() in text_lower:
                    affected.append(sys["otto_system"])
                    break
    return list(set(affected))


def generate_guardrails(vertical: str, category: str, description: str) -> dict:
    """Generate guardrail recommendations based on vertical and category."""
    desc_lower = description.lower()
    guardrails = {"review_required": True, "actions": [], "references": []}

    if vertical == "blockchain":
        if any(w in desc_lower for w in ["reentrancy", "re-entrancy"]):
            guardrails["actions"] = [
                "Audit all external calls for reentrancy",
                "Use ReentrancyGuard on state-changing functions",
                "Follow checks-effects-interactions pattern"
            ]
            guardrails["code_pattern"] = "nonReentrant modifier, ReentrancyGuard"
            guardrails["references"] = ["https://docs.openzeppelin.com/contracts/4.x/api/security#ReentrancyGuard"]
        elif any(w in desc_lower for w in ["integer overflow", "overflow", "underflow"]):
            guardrails["actions"] = ["Use Solidity 0.8+ for built-in overflow checks", "Audit SafeMath usage"]
        elif any(w in desc_lower for w in ["oracle", "price manipulation", "flash loan"]):
            guardrails["actions"] = [
                "Use TWAP oracle (Uniswap v3 TWAP, Chainlink)",
                "Add price deviation checks",
                "Implement circuit breakers"
            ]
        elif any(w in desc_lower for w in ["access control", "unauthorized"]):
            guardrails["actions"] = [
                "Audit all onlyOwner/onlyRole modifiers",
                "Use OpenZeppelin AccessControl",
                "Multi-sig for admin functions"
            ]
        else:
            guardrails["actions"] = ["Full smart contract audit before deployment", "Formal verification if critical"]

    elif vertical == "ai":
        if any(w in desc_lower for w in ["prompt injection", "jailbreak"]):
            guardrails["actions"] = [
                "Sanitize all user inputs before LLM injection",
                "Use system prompt hardening",
                "Implement output validation layer",
                "Never execute LLM-generated code without sandboxing"
            ]
        elif any(w in desc_lower for w in ["model extraction", "membership inference"]):
            guardrails["actions"] = [
                "Rate-limit API calls per user",
                "Add output perturbation/noise",
                "Monitor for systematic probing patterns"
            ]
        else:
            guardrails["actions"] = ["Review LLM integration for injection surfaces", "Add input/output filtering"]

    elif vertical == "vm_infra":
        if any(w in desc_lower for w in ["privilege escalation", "sudo", "setuid"]):
            guardrails["actions"] = [
                "Apply OS patch immediately",
                "Audit sudo rules and SUID binaries",
                "Run services with minimum required privileges"
            ]
        elif any(w in desc_lower for w in ["container escape", "docker"]):
            guardrails["actions"] = [
                "Update Docker to latest version",
                "Use rootless containers",
                "Audit container capabilities and seccomp profiles"
            ]
        else:
            guardrails["actions"] = ["Apply CVE patch", "Check affected package version", "Schedule maintenance window"]

    elif vertical == "web":
        if "xss" in desc_lower or "cross-site scripting" in desc_lower:
            guardrails["actions"] = [
                "Sanitize all user-controlled output",
                "Set Content-Security-Policy headers",
                "Use React/Next.js built-in escaping (never dangerouslySetInnerHTML with user input)"
            ]
        elif "sql" in desc_lower and "injection" in desc_lower:
            guardrails["actions"] = [
                "Use parameterized queries (asyncpg already does this)",
                "Audit all raw SQL strings",
                "Least privilege DB user per service"
            ]
        elif any(w in desc_lower for w in ["jwt", "auth", "session"]):
            guardrails["actions"] = [
                "Audit JWT secret strength and rotation policy",
                "Verify token expiry enforcement",
                "Check for algorithm confusion vulnerabilities"
            ]
        else:
            guardrails["actions"] = ["Dependency update", "Security headers audit", "OWASP Top 10 checklist review"]

    elif vertical == "network":
        guardrails["actions"] = [
            "Review firewall rules",
            "Enable TLS 1.3 minimum",
            "Monitor for anomalous traffic patterns"
        ]

    elif vertical == "mobile":
        guardrails["actions"] = [
            "Update affected dependency",
            "Audit deep link handling",
            "Review certificate pinning implementation"
        ]

    elif vertical == "robotics":
        guardrails["actions"] = [
            "Firmware update review",
            "Network isolation for IoT devices",
            "Physical access control audit"
        ]

    if not guardrails["actions"]:
        guardrails["actions"] = ["Review and assess impact", "Apply vendor patch if available"]

    return guardrails


async def upsert_vuln(conn, record: dict, system_map: list[dict]) -> str:
    """Insert or update a vulnerability record. Returns 'new', 'updated', or 'skip'."""
    content_hash = make_hash(record["source"], record["external_id"])

    existing = await conn.fetchrow(
        "SELECT id, updated_at FROM vulnerability_intelligence WHERE content_hash = $1",
        content_hash
    )

    full_text = f"{record.get('title', '')} {record.get('description', '')} {' '.join(record.get('affected_products', []))}"
    affected_otto = map_to_otto_systems(full_text, system_map)

    vertical = record.get("vertical") or classify_vertical(full_text)
    category = record.get("category", "")
    severity = record.get("severity") or cvss_to_severity(record.get("cvss_score"))
    guardrails = generate_guardrails(vertical, category, record.get("description", ""))

    if existing:
        # Update existing record
        await conn.execute("""
            UPDATE vulnerability_intelligence SET
                title = $1, description = $2, severity = $3, cvss_score = $4,
                affected_products = $5, affected_otto_systems = $6,
                guardrails = $7, source_url = $8, updated_at = NOW()
            WHERE content_hash = $9
        """,
            record["title"], record["description"], severity, record.get("cvss_score"),
            record.get("affected_products", []), affected_otto,
            json.dumps(guardrails), record.get("source_url"),
            content_hash
        )
        return "updated"
    else:
        await conn.execute("""
            INSERT INTO vulnerability_intelligence
                (title, cve_id, external_id, vertical, category, attack_vector, severity, cvss_score,
                 cvss_vector, source, source_url, raw_data, description, affected_products,
                 affected_otto_systems, financial_loss_usd, guardrails, published_at, content_hash)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
        """,
            record["title"], record.get("cve_id"), record["external_id"],
            vertical, category, record.get("attack_vector"),
            severity, record.get("cvss_score"), record.get("cvss_vector"),
            record["source"], record.get("source_url"),
            json.dumps(record.get("raw_data", {})),
            record["description"],
            record.get("affected_products", []),
            affected_otto,
            record.get("financial_loss_usd"),
            json.dumps(guardrails),
            record.get("published_at"),
            content_hash
        )
        return "new"


# ─── NVD / CVE Collector ─────────────────────────────────────────────────────

async def fetch_nvd_cves(session: aiohttp.ClientSession, days_back: int = 7) -> list[dict]:
    """Fetch recent CVEs from NVD API v2. No auth needed for public data."""
    records = []
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)

    # Each entry = (keyword, vertical) — one API call per keyword to avoid AND semantics
    keyword_sets = [
        ("docker", "vm_infra"),
        ("linux kernel privilege", "vm_infra"),
        ("nginx apache", "web"),
        ("xss injection", "web"),
        ("android", "mobile"),
        ("ios", "mobile"),
        ("solidity", "blockchain"),
        ("ethereum", "blockchain"),
        ("tensorflow", "ai"),
        ("pytorch", "ai"),
    ]

    for keywords_str, vertical in keyword_sets:
        params = {
            "pubStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "keywordSearch": keywords_str,
            "resultsPerPage": 20,
        }
        try:
            async with session.get(NVD_API, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    log.warning(f"NVD API returned {resp.status} for keywords: {keywords_str}")
                    continue
                data = await resp.json()
                vulns = data.get("vulnerabilities", [])
                log.info(f"NVD: {len(vulns)} CVEs for [{vertical}] '{keywords_str}'")

                for item in vulns:
                    cve = item.get("cve", {})
                    cve_id = cve.get("id", "")
                    if not cve_id:
                        continue

                    # Extract description (English preferred)
                    descriptions = cve.get("descriptions", [])
                    desc = next(
                        (d["value"] for d in descriptions if d.get("lang") == "en"),
                        descriptions[0]["value"] if descriptions else ""
                    )

                    # Extract CVSS score
                    metrics = cve.get("metrics", {})
                    cvss_score = None
                    cvss_vector = None
                    for metric_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                        metric_list = metrics.get(metric_key, [])
                        if metric_list:
                            cvss_data = metric_list[0].get("cvssData", {})
                            cvss_score = cvss_data.get("baseScore")
                            cvss_vector = cvss_data.get("vectorString")
                            break

                    # Extract affected products
                    affected_products = []
                    for config in cve.get("configurations", []):
                        for node in config.get("nodes", []):
                            for cpe_match in node.get("cpeMatch", []):
                                cpe = cpe_match.get("criteria", "")
                                # Extract product name from CPE: cpe:2.3:a:vendor:product:...
                                parts = cpe.split(":")
                                if len(parts) > 4:
                                    affected_products.append(parts[4])

                    published_at = None
                    if pub := cve.get("published"):
                        try:
                            published_at = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    records.append({
                        "title": f"{cve_id}: {desc[:100]}",
                        "cve_id": cve_id,
                        "external_id": cve_id,
                        "vertical": vertical,
                        "category": "cve",
                        "severity": cvss_to_severity(cvss_score),
                        "cvss_score": cvss_score,
                        "cvss_vector": cvss_vector,
                        "source": "nvd",
                        "source_url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                        "description": desc,
                        "affected_products": list(set(affected_products[:20])),
                        "published_at": published_at,
                        "raw_data": {"cve_id": cve_id, "metrics": metrics},
                    })

        except Exception as e:
            log.error(f"NVD fetch error for [{vertical}]: {e}")
        await asyncio.sleep(1)  # NVD rate limit: ~1 req/sec without API key

    return records


# ─── DeFiHackLabs Collector ───────────────────────────────────────────────────

async def fetch_defihacklabs(session: aiohttp.ClientSession) -> list[dict]:
    """Parse DeFiHackLabs README for historical blockchain exploit data.
    Format (heading-based):
        ### 20260310 AlkemiEarn - Business Logic
        ### Lost: 43.45 ETH
        ...
        https://x.com/... (link)
    """
    records = []
    try:
        async with session.get(DEFIHACKLABS_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                log.warning(f"DeFiHackLabs returned {resp.status}")
                return []
            content = await resp.text()

        # Pattern: ### YYYYMMDD Protocol - Attack Type
        incident_pattern = re.compile(
            r'^### (\d{8})\s+([^-\n]+?)\s*-\s*([^\n]+)',
            re.MULTILINE
        )
        # Pattern: ### Lost: amount (optional)
        lost_pattern = re.compile(r'Lost[:\s]+([^\n]+)', re.IGNORECASE)
        # Pattern: any URL (first one after the incident header)
        url_pattern = re.compile(r'https?://\S+')

        # Split into sections by incident header
        sections = re.split(r'(?=^### \d{8})', content, flags=re.MULTILINE)

        seen = set()
        for section in sections:
            m = incident_pattern.match(section.strip())
            if not m:
                continue

            date_str = m.group(1).strip()
            protocol = m.group(2).strip()
            attack_type = m.group(3).strip()

            dedup_key = f"{date_str}:{protocol.lower()}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # Parse date
            published_at = None
            try:
                published_at = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
            except Exception:
                pass

            # Parse loss
            financial_loss = None
            lost_m = lost_pattern.search(section)
            funds_lost_str = ""
            if lost_m:
                funds_lost_str = lost_m.group(1).strip()
                # Extract numeric part with multiplier
                num_m = re.search(r'([\d,]+\.?\d*)\s*([KMBkmb])?', funds_lost_str)
                if num_m:
                    try:
                        val = float(num_m.group(1).replace(',', ''))
                        multiplier = num_m.group(2) or ''
                        if multiplier.upper() == 'B':
                            val *= 1_000_000_000
                        elif multiplier.upper() == 'M':
                            val *= 1_000_000
                        elif multiplier.upper() == 'K':
                            val *= 1_000
                        # Convert ETH/BNB to approximate USD (rough: $2000/ETH, $300/BNB)
                        if 'ETH' in funds_lost_str.upper():
                            val *= 2000
                        elif 'BNB' in funds_lost_str.upper():
                            val *= 300
                        financial_loss = int(val)
                    except Exception:
                        pass

            # Severity
            if financial_loss and financial_loss > 10_000_000:
                severity = "CRITICAL"
            elif financial_loss and financial_loss > 1_000_000:
                severity = "HIGH"
            elif financial_loss and financial_loss > 100_000:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            # Link reference
            link = ""
            url_m = url_pattern.search(section[m.end():])
            if url_m:
                link = url_m.group(0).rstrip(')')

            category = re.sub(r'[^a-z0-9_]', '_', attack_type.lower())[:50]
            external_id = f"dhl-{date_str}-{re.sub(r'[^a-z0-9]', '', protocol.lower())[:20]}"

            description = (
                f"{protocol} was exploited via {attack_type}. "
                f"Estimated loss: {funds_lost_str or 'unknown'}. "
                f"Date: {date_str}."
            )
            if link:
                description += f" Ref: {link}"

            records.append({
                "title": f"[DeFiHackLabs] {protocol} — {attack_type}",
                "external_id": external_id,
                "vertical": "blockchain",
                "category": category,
                "severity": severity,
                "source": "defihacklabs",
                "source_url": link or f"https://github.com/SunWeb3Sec/DeFiHackLabs",
                "description": description,
                "affected_products": [protocol.lower()],
                "financial_loss_usd": financial_loss,
                "published_at": published_at,
                "raw_data": {
                    "date": date_str,
                    "protocol": protocol,
                    "funds_lost": funds_lost_str,
                    "attack_type": attack_type,
                },
            })

    except Exception as e:
        log.error(f"DeFiHackLabs fetch error: {e}")
        import traceback
        log.error(traceback.format_exc())

    log.info(f"DeFiHackLabs: {len(records)} exploit records parsed")
    return records


# ─── AI Security / MITRE ATLAS ───────────────────────────────────────────────

ATLAS_TECHNIQUES_URL = "https://raw.githubusercontent.com/mitre-atlas/atlas-data/main/data/techniques.yaml"

AI_KNOWN_VULNS = [
    {
        "external_id": "ai-prompt-injection-001",
        "title": "Indirect Prompt Injection via Tool Outputs",
        "category": "prompt_injection",
        "severity": "CRITICAL",
        "description": (
            "Attackers embed adversarial instructions in external content (web pages, documents, "
            "tool outputs) that the LLM agent reads and executes. Particularly dangerous for "
            "autonomous agents that browse the web or process external documents."
        ),
        "affected_products": ["langchain", "claude", "chatgpt", "gpt-4", "autonomous agents"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0051.000",
        "cvss_score": 9.1,
    },
    {
        "external_id": "ai-jailbreak-001",
        "title": "System Prompt Extraction and Jailbreak via Role Play",
        "category": "jailbreak",
        "severity": "HIGH",
        "description": (
            "Attackers use role-play, hypothetical scenarios, or encoded payloads to bypass "
            "system prompt safety guidelines and extract system instructions or execute "
            "disallowed actions."
        ),
        "affected_products": ["claude", "gpt-4", "llm apis"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0054",
        "cvss_score": 7.5,
    },
    {
        "external_id": "ai-tool-abuse-001",
        "title": "Malicious Code Execution via LLM Tool Calls",
        "category": "code_execution",
        "severity": "CRITICAL",
        "description": (
            "LLM agents with code execution capabilities (bash, Python REPL) can be manipulated "
            "into executing attacker-controlled commands via prompt injection or adversarial inputs. "
            "Critical for autonomous agents with shell access like Otto."
        ),
        "affected_products": ["claude code", "openai assistants", "autonomous agents with shell"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0051",
        "cvss_score": 9.8,
    },
    {
        "external_id": "ai-model-extraction-001",
        "title": "Model Extraction via Systematic API Queries",
        "category": "model_extraction",
        "severity": "MEDIUM",
        "description": (
            "Adversaries reconstruct model functionality through systematic API queries. "
            "Relevant for any fine-tuned model exposed via API."
        ),
        "affected_products": ["ml apis", "inference endpoints"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0044",
        "cvss_score": 5.3,
    },
    {
        "external_id": "ai-data-poisoning-001",
        "title": "Training Data Poisoning via Supply Chain",
        "category": "data_poisoning",
        "severity": "HIGH",
        "description": (
            "Attackers poison training datasets (including public datasets, web scrapes, "
            "or RLHF feedback) to introduce backdoors or degrade model performance."
        ),
        "affected_products": ["hugging face datasets", "open datasets", "rlhf pipelines"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0020",
        "cvss_score": 7.8,
    },
    {
        "external_id": "ai-adversarial-example-001",
        "title": "Adversarial Examples Against Vision Models",
        "category": "adversarial_input",
        "severity": "MEDIUM",
        "description": (
            "Imperceptible perturbations to images cause misclassification. Relevant for "
            "any vision pipeline in Otto hardware or Shakrah health monitoring."
        ),
        "affected_products": ["vision models", "image classifiers", "opencv"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0043",
        "cvss_score": 5.8,
    },
    {
        "external_id": "ai-supply-chain-001",
        "title": "Malicious ML Model in Public Repository",
        "category": "supply_chain",
        "severity": "HIGH",
        "description": (
            "Malicious models uploaded to HuggingFace or other repositories contain embedded "
            "backdoors, trojans, or pickle deserialization exploits. "
            "torch.load() on untrusted checkpoints executes arbitrary code."
        ),
        "affected_products": ["hugging face", "pytorch", "tensorflow", "onnx"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0010",
        "cvss_score": 8.2,
    },
    {
        "external_id": "ai-context-manipulation-001",
        "title": "Context Window Manipulation in Multi-Turn Agents",
        "category": "context_manipulation",
        "severity": "HIGH",
        "description": (
            "Attackers craft long conversations or inject prior context to shift agent behavior "
            "across turns. Stateful agents (like Otto) that maintain conversation history are "
            "especially vulnerable. Context rot amplifies this — degraded reasoning in long "
            "contexts makes manipulation easier."
        ),
        "affected_products": ["autonomous agents", "claude code", "stateful llm"],
        "source": "atlas",
        "source_url": "https://atlas.mitre.org/techniques/AML.T0054",
        "cvss_score": 7.3,
    },
]


async def fetch_ai_vulns() -> list[dict]:
    """Return curated AI security vulnerabilities (ATLAS-based + known patterns)."""
    records = []
    for vuln in AI_KNOWN_VULNS:
        records.append({
            **vuln,
            "vertical": "ai",
            "published_at": datetime(2024, 1, 1, tzinfo=timezone.utc),  # Approximate
        })
    log.info(f"AI/ATLAS: {len(records)} curated vulnerability records")
    return records


# ─── Blockchain-Specific Known Patterns ──────────────────────────────────────

BLOCKCHAIN_KNOWN_VULNS = [
    {
        "external_id": "bc-reentrancy-001",
        "title": "Reentrancy Attack Pattern (DAO-style)",
        "category": "reentrancy",
        "severity": "CRITICAL",
        "description": (
            "Attacker contract calls back into victim before state is updated. "
            "Most notorious: The DAO hack ($60M, 2016). "
            "Mitigation: checks-effects-interactions, ReentrancyGuard."
        ),
        "affected_products": ["solidity", "evm", "smart contracts"],
        "cvss_score": 9.8,
        "source": "manual",
        "source_url": "https://consensys.github.io/smart-contract-best-practices/attacks/reentrancy/",
    },
    {
        "external_id": "bc-flashloan-oracle-001",
        "title": "Flash Loan Oracle Price Manipulation",
        "category": "oracle_manipulation",
        "severity": "CRITICAL",
        "description": (
            "Attacker uses flash loan to temporarily skew DEX spot price, "
            "triggering protocol actions at manipulated price. "
            "DeFi hacks using this: Harvest Finance ($34M), bZx ($1M), Mango Markets ($114M)."
        ),
        "affected_products": ["aave", "uniswap v2", "compound", "any spot-price oracle"],
        "cvss_score": 9.5,
        "source": "manual",
        "source_url": "https://medium.com/@hacxyk/we-rescued-34m-from-harvest-finance-but-was-it-worth-it-5e6b0553f0de",
    },
    {
        "external_id": "bc-access-control-001",
        "title": "Missing Access Control on Admin Functions",
        "category": "access_control",
        "severity": "CRITICAL",
        "description": (
            "Admin-only functions (mint, burn, pause, upgrade) lack onlyOwner/onlyRole "
            "or use tx.origin instead of msg.sender. "
            "Common in rushed deployments. Use OpenZeppelin Ownable + AccessControl."
        ),
        "affected_products": ["solidity", "erc20 tokens", "proxy contracts"],
        "cvss_score": 9.3,
        "source": "manual",
        "source_url": "https://swcregistry.io/docs/SWC-105",
    },
    {
        "external_id": "bc-proxy-storage-001",
        "title": "Storage Collision in Proxy Upgrade Pattern",
        "category": "storage_collision",
        "severity": "HIGH",
        "description": (
            "Upgradeable proxy contracts can corrupt storage if implementation and proxy "
            "use same storage slots. EIP-1967 unstructured storage + OpenZeppelin TransparentProxy "
            "or UUPS are safe patterns."
        ),
        "affected_products": ["proxy contracts", "transparent proxy", "uups", "upgradeable"],
        "cvss_score": 8.5,
        "source": "manual",
        "source_url": "https://docs.openzeppelin.com/upgrades-plugins/1.x/proxies#storage-collisions-between-implementation-versions",
    },
    {
        "external_id": "bc-frontrun-001",
        "title": "MEV / Front-Running on Token Launch",
        "category": "mev_frontrun",
        "severity": "HIGH",
        "description": (
            "Bots monitor mempool, copy transactions with higher gas to extract value. "
            "Particularly damaging on token launches and AMM swaps. "
            "Mitigations: commit-reveal, batch auctions, private RPC (Flashbots Protect)."
        ),
        "affected_products": ["uniswap", "amm", "token launches", "mev"],
        "cvss_score": 7.5,
        "source": "manual",
        "source_url": "https://www.flashbots.net/",
    },
    {
        "external_id": "bc-eip7702-txorigin-001",
        "title": "EIP-7702 Breaks tx.origin Anti-Bot Check (Ethereum Pectra)",
        "category": "protocol_change",
        "severity": "HIGH",
        "description": (
            "After Ethereum Pectra upgrade (May 2025), EIP-7702 allows EOAs to have code. "
            "This breaks require(msg.sender == tx.origin) anti-bot guard — "
            "EOAs can now be delegated to contracts while msg.sender == tx.origin still holds. "
            "Any contract using this pattern for bot protection is now vulnerable on Ethereum mainnet."
        ),
        "affected_products": ["ethereum", "solidity", "evm", "erc20", "defi"],
        "cvss_score": 7.2,
        "source": "manual",
        "source_url": "https://eips.ethereum.org/EIPS/eip-7702",
    },
]


async def fetch_blockchain_vulns() -> list[dict]:
    """Return curated blockchain vulnerability patterns."""
    records = []
    for vuln in BLOCKCHAIN_KNOWN_VULNS:
        records.append({
            **vuln,
            "vertical": "blockchain",
            "published_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        })
    log.info(f"Blockchain curated: {len(records)} records")
    return records


# ─── Main Sync Function ───────────────────────────────────────────────────────

async def run_sync(sources: Optional[list[str]] = None, days_back: int = 7):
    """Run the full vulnerability sync. sources=None means all."""
    if sources is None:
        sources = ["nvd", "defihacklabs", "ai_atlas", "blockchain_curated"]

    # Load env for DB password
    env_file = "/home/web3relic/memory/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    db_pass = os.getenv("POSTGRES_PASSWORD", "")

    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=db_pass
    )

    system_map = await get_system_map(conn)
    log.info(f"Loaded {len(system_map)} Otto system mappings")

    total_new = 0
    total_updated = 0

    async with aiohttp.ClientSession(headers={"User-Agent": "Otto-SecurityBot/1.0"}) as session:

        for source in sources:
            # Log sync start
            sync_id = await conn.fetchval(
                "INSERT INTO vuln_sync_log (source) VALUES ($1) RETURNING id",
                source
            )

            try:
                records = []
                if source == "nvd":
                    records = await fetch_nvd_cves(session, days_back=days_back)
                elif source == "defihacklabs":
                    records = await fetch_defihacklabs(session)
                elif source == "ai_atlas":
                    records = await fetch_ai_vulns()
                elif source == "blockchain_curated":
                    records = await fetch_blockchain_vulns()

                new_count = 0
                updated_count = 0
                for record in records:
                    result = await upsert_vuln(conn, record, system_map)
                    if result == "new":
                        new_count += 1
                    elif result == "updated":
                        updated_count += 1

                total_new += new_count
                total_updated += updated_count

                await conn.execute("""
                    UPDATE vuln_sync_log SET
                        completed_at = NOW(), records_fetched = $1,
                        records_new = $2, records_updated = $3, status = 'success'
                    WHERE id = $4
                """, len(records), new_count, updated_count, sync_id)

                log.info(f"[{source}] Done: {new_count} new, {updated_count} updated, {len(records)} total")

            except Exception as e:
                log.error(f"[{source}] Sync error: {e}")
                await conn.execute(
                    "UPDATE vuln_sync_log SET completed_at = NOW(), error = $1, status = 'error' WHERE id = $2",
                    str(e), sync_id
                )

    await conn.close()

    log.info(f"Sync complete: {total_new} new vulns, {total_updated} updated")
    return {"new": total_new, "updated": total_updated}


if __name__ == "__main__":
    import sys
    sources = sys.argv[1:] if len(sys.argv) > 1 else None
    result = asyncio.run(run_sync(sources=sources, days_back=30))
    print(json.dumps(result))
