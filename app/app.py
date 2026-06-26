import os
import time
import shutil
import psutil
import requests
import importlib.util
import importlib
import pkgutil
import inspect
import traceback
import threading
from queue import Queue, Empty
from requests.exceptions import RequestException
from datetime import datetime, timezone

from dotenv import dotenv_values
from flask import Flask, render_template, jsonify, request, send_file
import subprocess

app = Flask(__name__)

# ---------------------------------------------------------------------------
# TRADING CENTER – Asset catalogue (read-only, display metadata only)
# ---------------------------------------------------------------------------
TRADING_ASSETS = {
    "XAUUSD": {"display_name": "XAU/USD", "label": "Gold"},
    "GER40":  {"display_name": "GER40",   "label": "DAX"},
    "US500":  {"display_name": "US500",   "label": "S&P 500"},
    "EURUSD": {"display_name": "EUR/USD", "label": "Euro / US-Dollar"},
    "GBPUSD": {"display_name": "GBP/USD", "label": "Britisches Pfund"},
    "BTCUSD": {"display_name": "BTC/USD", "label": "Bitcoin"},
    "ETHUSD": {"display_name": "ETH/USD", "label": "Ethereum"},
}

CTRADER_API_CANDIDATES = {
    "demo": [
        "https://api.ctrader.com",
        "https://openapi.ctrader.com",
    ],
    "live": [
        "https://api.ctrader.com",
        "https://openapi.ctrader.com",
    ],
}

CTRADER_SYMBOL_MAP = {}
CTRADER_SYMBOL_CATALOG = {}
CTRADER_SYMBOL_CATALOG_TS = 0
CTRADER_QUOTE_CACHE = {}
CTRADER_SPOT_PRICE_SCALE = 100000.0
CTRADER_SPOT_PRICE_RAW_THRESHOLD = 10000.0
CTRADER_SPOT_SPREAD_RAW_THRESHOLD = 1.0
CTRADER_STREAM_STATUS = {
    "status": "stopped",
    "started_at": "",
    "connected": False,
    "subscribed_symbols": [],
    "subscribed_symbol_ids": [],
    "last_event_at": "",
    "last_message_at": "",
    "last_payload_type": "",
    "last_message_fields": [],
    "last_spot_event_fields": [],
    "last_spot_event_dict": {},
    "last_spot_symbol_id": "",
    "last_error": "",
    "callback_invoked_count": 0,
    "received_payload_types": [],
    "subscribe_requests_sent": 0,
    "subscribe_responses_received": 0,
    "subscribe_errors": 0,
    "spot_event_count": 0,
}
CTRADER_STREAM_THREAD = None
CTRADER_STREAM_STOP_EVENT = threading.Event()
CTRADER_STREAM_LOCK = threading.Lock()
CTRADER_KNOWN_SYMBOL_FALLBACK = {
    "EURUSD": {"symbol_id": "1", "symbolName": "EURUSD", "description": "Euro vs US Dollar"},
    "GBPUSD": {"symbol_id": "2", "symbolName": "GBPUSD", "description": "British Pound vs US Dollar"},
    "XAUUSD": {"symbol_id": "41", "symbolName": "XAUUSD", "description": "Gold vs US Dollar"},
    "BTCUSD": {"symbol_id": "101", "symbolName": "BTCUSD", "description": "Bitcoin vs US Dollar"},
    "ETHUSD": {"symbol_id": "102", "symbolName": "ETHUSD", "description": "Ethereum vs US Dollar"},
}

def _get_local_env():
    """Read cTrader/OpenRouter secrets from preferred local env files."""
    candidates = [
        r"/home/ramses/.hermes/.env",
        r"\\wsl$\Ubuntu\home\ramses\.hermes\.env",
        os.path.join(os.path.dirname(__file__), ".env"),
    ]
    values = {}
    for path in candidates:
        try:
            if os.path.exists(path):
                values.update({k: v for k, v in dotenv_values(path).items() if v is not None})
        except Exception:
            continue
    return values

def _get_ctrader_credentials():
    """Return cTrader credentials from local .env or None if missing."""
    env = _get_local_env()
    client_id     = env.get("CTRADER_CLIENT_ID", "").strip()
    client_secret = env.get("CTRADER_CLIENT_SECRET", "").strip()
    account_id    = env.get("CTRADER_ACCOUNT_ID", "").strip()
    if client_id and client_secret and account_id:
        return client_id, client_secret, account_id
    return None


def _get_ctrader_env_label():
    env = _get_local_env()
    return (env.get("CTRADER_ENV", "demo") or "demo").strip().lower()


def _get_ctrader_runtime():
    env = _get_local_env()
    return {
        "client_id": (env.get("CTRADER_CLIENT_ID") or "").strip(),
        "client_secret": (env.get("CTRADER_CLIENT_SECRET") or "").strip(),
        "access_token": (env.get("CTRADER_ACCESS_TOKEN") or "").strip(),
        "refresh_token": (env.get("CTRADER_REFRESH_TOKEN") or "").strip(),
        "account_id": (env.get("CTRADER_ACCOUNT_ID") or "").strip(),
        "env": (env.get("CTRADER_ENV", "demo") or "demo").strip().lower(),
    }


def _get_env_status():
    candidates = [
        r"/home/ramses/.hermes/.env",
        r"\\wsl$\Ubuntu\home\ramses\.hermes\.env",
        os.path.join(os.path.dirname(__file__), ".env"),
    ]
    used_path = None
    found = False
    values = {}
    for path in candidates:
        try:
            if os.path.exists(path):
                parsed = dotenv_values(path)
                values = {k: v for k, v in parsed.items() if v is not None}
                used_path = path
                found = True
                break
        except Exception:
            continue

    return {
        "env_file_found": found,
        "env_path_used": used_path,
        "client_id_present": bool((values.get("CTRADER_CLIENT_ID") or "").strip()),
        "client_secret_present": bool((values.get("CTRADER_CLIENT_SECRET") or "").strip()),
        "access_token_present": bool((values.get("CTRADER_ACCESS_TOKEN") or "").strip()),
        "refresh_token_present": bool((values.get("CTRADER_REFRESH_TOKEN") or "").strip()),
        "account_id_present": bool((values.get("CTRADER_ACCOUNT_ID") or "").strip()),
        "env_present": bool((values.get("CTRADER_ENV") or "").strip()),
    }


def _normalize_ctrader_symbol(symbol):
    symbol = (symbol or "").strip().upper()
    if symbol == "XAUUSD":
        return "XAUUSD", "XAU/USD"
    if symbol == "GER40":
        return "GER40", "GER40"
    if symbol == "US500":
        return "US500", "US500"
    if symbol == "EURUSD":
        return "EURUSD", "EUR/USD"
    if symbol == "GBPUSD":
        return "GBPUSD", "GBP/USD"
    if symbol == "BTCUSD":
        return "BTCUSD", "BTC/USD"
    if symbol == "ETHUSD":
        return "ETHUSD", "ETH/USD"
    return symbol, symbol


def _build_trading_response(symbol, status="offline", message=""):
    asset = TRADING_ASSETS.get(symbol, {"display_name": symbol, "label": symbol})
    return {
        "status": status,
        "provider": "cTrader",
        "mode": "read_only",
        "symbol": symbol,
        "symbol_id": "",
        "display_name": asset["display_name"],
        "description": asset["label"],
        "label": asset["label"],
        "bid": None,
        "ask": None,
        "spread": None,
        "last_price": None,
        "updated_at": None,
        "message": message,
    }


def _ctrader_auth_headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _extract_ctrader_error(response):
    try:
        data = response.json()
        msg = data.get("message") or data.get("error") or data.get("error_description")
        if msg:
            return str(msg)
    except Exception:
        pass
    return (response.text or "").strip()[:240]


def _parse_ctrader_symbols(payload):
    raw_items = []
    if isinstance(payload, dict):
        for key in ("symbols", "data", "items", "instruments"):
            value = payload.get(key)
            if isinstance(value, list):
                raw_items = value
                break
        if not raw_items:
            for value in payload.values():
                if isinstance(value, list):
                    raw_items = value
                    break
    elif isinstance(payload, list):
        raw_items = payload

    parsed = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        symbol_id = (
            item.get("symbol_id")
            or item.get("symbolId")
            or item.get("id")
            or item.get("symbol")
            or item.get("name")
        )
        if not symbol_id:
            continue
        parsed.append({
            "symbol_id": str(symbol_id),
            "name": str(item.get("name") or item.get("symbol") or symbol_id),
            "display_name": str(item.get("display_name") or item.get("displayName") or item.get("description") or item.get("name") or symbol_id),
            "base_asset": str(item.get("base_asset") or item.get("baseAsset") or item.get("baseCurrency") or item.get("base") or ""),
            "quote_asset": str(item.get("quote_asset") or item.get("quoteAsset") or item.get("quoteCurrency") or item.get("quote") or ""),
        })
    return parsed


def _store_ctrader_symbol_map(symbols):
    global CTRADER_SYMBOL_MAP, CTRADER_SYMBOL_CATALOG, CTRADER_SYMBOL_CATALOG_TS
    mapping = {}
    catalog = {}
    for item in symbols:
        symbol_id = item.get("symbol_id") or item.get("symbolId") or item.get("id")
        name = (item.get("name") or item.get("symbol_name") or item.get("symbolName") or item.get("symbol") or "").upper()
        display_name = item.get("display_name") or item.get("displayName") or item.get("description") or item.get("name") or item.get("symbol_name") or item.get("symbolName") or name
        description = item.get("description") or item.get("display_name") or item.get("displayName") or display_name
        if not name or not symbol_id:
            continue
        mapping[name] = symbol_id
        if "/" in name:
            mapping[name.replace("/", "")] = symbol_id
        if item.get("symbol_name"):
            mapping[str(item["symbol_name"]).upper()] = symbol_id
        if item.get("symbolName"):
            mapping[str(item["symbolName"]).upper()] = symbol_id
        if display_name:
            mapping[str(display_name).upper()] = symbol_id
        raw_name = " ".join([name, str(display_name), str(description)]).upper()
        compact = raw_name.replace(" ", "").replace("/", "").replace("-", "").replace(".", "")
        if ("US 500" in raw_name or "US500" in compact or "SPX500" in compact or "SP500" in compact) and bool(item.get("enabled", True)):
            mapping.setdefault("US500", symbol_id)
            mapping.setdefault("S&P500", symbol_id)
            mapping.setdefault("SPX500", symbol_id)
            mapping.setdefault("SP500", symbol_id)
        if ("GERMANY 40" in raw_name or "GER 40" in raw_name or "GER40" in compact or "DAX40" in compact) and bool(item.get("enabled", True)):
            mapping.setdefault("GER40", symbol_id)
            mapping.setdefault("DAX40", symbol_id)
        catalog[symbol_id] = {
            "symbol_id": str(symbol_id),
            "symbolName": str(item.get("symbol_name") or item.get("symbolName") or item.get("name") or ""),
            "symbol_name": str(item.get("symbol_name") or item.get("symbolName") or item.get("name") or ""),
            "display_name": str(display_name),
            "description": str(description),
            "enabled": bool(item.get("enabled", True)),
            "base_asset_id": str(item.get("base_asset_id") or item.get("baseAssetId") or ""),
            "quote_asset_id": str(item.get("quote_asset_id") or item.get("quoteAssetId") or ""),
        }
    CTRADER_SYMBOL_MAP = mapping
    CTRADER_SYMBOL_CATALOG = catalog
    CTRADER_SYMBOL_CATALOG_TS = time.time()


def _resolve_ctrader_symbol_id(symbol):
    normalized_symbol, _ = _normalize_ctrader_symbol(symbol)
    upper = normalized_symbol.upper()
    symbol_id = CTRADER_SYMBOL_MAP.get(upper) or CTRADER_SYMBOL_MAP.get(upper.replace("/", ""))
    if symbol_id:
        return symbol_id
    if upper in ("US500", "GER40"):
        for item_symbol_id, meta in CTRADER_SYMBOL_CATALOG.items():
            text = " ".join([
                str(meta.get("symbolName", "")),
                str(meta.get("symbol_name", "")),
                str(meta.get("display_name", "")),
                str(meta.get("description", "")),
            ]).upper()
            if upper == "US500" and ("US 500" in text or "US500" in text or "SPX500" in text or "SP500" in text) and bool(meta.get("enabled", True)):
                return item_symbol_id
            if upper == "GER40" and ("GERMANY 40" in text or "GER 40" in text or "GER40" in text or "DAX40" in text) and bool(meta.get("enabled", True)):
                return item_symbol_id
    return ""


def _resolve_ctrader_symbol_meta(symbol):
    normalized_symbol, display_name = _normalize_ctrader_symbol(symbol)
    upper = normalized_symbol.upper()
    symbol_id = _resolve_ctrader_symbol_id(symbol)
    if symbol_id and symbol_id in CTRADER_SYMBOL_CATALOG:
        return CTRADER_SYMBOL_CATALOG[symbol_id]
    return {
        "symbol_id": str(symbol_id or ""),
        "symbolName": upper,
        "symbol_name": upper,
        "display_name": display_name,
        "description": display_name,
        "enabled": True,
        "base_asset_id": "",
        "quote_asset_id": "",
    }


def get_mapped_symbol(symbol, runtime=None, ensure_cache=True):
    normalized_symbol, display_name = _normalize_ctrader_symbol(symbol)
    upper = normalized_symbol.upper()
    runtime = runtime or _get_ctrader_runtime()
    mapping_source = "cache"

    if ensure_cache and not CTRADER_SYMBOL_MAP:
        try:
            _ensure_ctrader_symbol_cache(runtime)
        except Exception:
            pass

    symbol_id = str(
        CTRADER_SYMBOL_MAP.get(upper)
        or CTRADER_SYMBOL_MAP.get(upper.replace("/", ""))
        or _resolve_ctrader_symbol_id(normalized_symbol)
        or ""
    )

    meta = _resolve_ctrader_symbol_meta(normalized_symbol)
    if not symbol_id:
        fallback = CTRADER_KNOWN_SYMBOL_FALLBACK.get(upper)
        if fallback:
            mapping_source = "known_fallback"
            symbol_id = fallback["symbol_id"]
            meta = {
                "symbol_id": symbol_id,
                "symbolName": fallback["symbolName"],
                "symbol_name": fallback["symbolName"],
                "display_name": display_name,
                "description": fallback["description"],
                "enabled": True,
                "base_asset_id": "",
                "quote_asset_id": "",
            }
        else:
            mapping_source = "unmapped"

    return {
        "symbol": upper,
        "symbol_id": str(symbol_id or ""),
        "symbolName": meta.get("symbolName") or upper,
        "symbol_name": meta.get("symbol_name") or meta.get("symbolName") or upper,
        "description": meta.get("description") or display_name,
        "display_name": meta.get("display_name") or display_name,
        "enabled": bool(meta.get("enabled", True)),
        "base_asset_id": meta.get("base_asset_id", ""),
        "quote_asset_id": meta.get("quote_asset_id", ""),
        "mapping_source": mapping_source,
        "cache_size": len(CTRADER_SYMBOL_MAP),
        "known_symbols_sample": list(sorted(CTRADER_KNOWN_SYMBOL_FALLBACK.keys())),
    }


def _ctrader_float(value):
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def _ctrader_scale_spot_price(value):
    value_f = _ctrader_float(value)
    if value_f is None:
        return None
    if abs(value_f) >= CTRADER_SPOT_PRICE_RAW_THRESHOLD:
        return value_f / CTRADER_SPOT_PRICE_SCALE
    return value_f


def _ctrader_scale_spot_spread(value):
    value_f = _ctrader_float(value)
    if value_f is None:
        return None
    if abs(value_f) >= CTRADER_SPOT_SPREAD_RAW_THRESHOLD:
        return value_f / CTRADER_SPOT_PRICE_SCALE
    return value_f


def _ctrader_extract_spot_quote(message):
    raw = _ctrader_message_to_dict(message)
    candidates = [
        raw,
        raw.get("payload") if isinstance(raw, dict) else None,
        raw.get("spot") if isinstance(raw, dict) else None,
        raw.get("spotEvent") if isinstance(raw, dict) else None,
        raw.get("spot_event") if isinstance(raw, dict) else None,
        raw.get("data") if isinstance(raw, dict) else None,
    ]
    flat = {}
    for candidate in candidates:
        if isinstance(candidate, dict):
            flat.update(candidate)

    def pick(*names):
        for name in names:
            if name in flat and flat[name] not in (None, ""):
                return flat[name]
        return None

    bid = pick("bid", "bidPrice", "bid_price")
    ask = pick("ask", "askPrice", "ask_price")
    last = pick("lastPrice", "last_price", "price", "closePrice", "close_price")
    spread = pick("spread")
    raw_bid_f = _ctrader_float(bid)
    raw_ask_f = _ctrader_float(ask)
    raw_last_f = _ctrader_float(last)
    raw_spread_f = _ctrader_float(spread)
    bid_f = _ctrader_scale_spot_price(bid)
    ask_f = _ctrader_scale_spot_price(ask)
    last_f = _ctrader_scale_spot_price(last)
    spread_f = _ctrader_scale_spot_spread(spread)
    if spread_f is None and bid_f is not None and ask_f is not None:
        spread_f = round(ask_f - bid_f, 10)
    if last_f is None and bid_f is not None and ask_f is not None:
        last_f = round((bid_f + ask_f) / 2.0, 10)
    return {
        "raw": raw,
        "raw_bid": raw_bid_f,
        "raw_ask": raw_ask_f,
        "raw_spread": raw_spread_f,
        "raw_last_price": raw_last_f,
        "price_scale": CTRADER_SPOT_PRICE_SCALE,
        "bid": bid_f,
        "ask": ask_f,
        "spread": spread_f,
        "last_price": last_f,
    }


def _ctrader_package_installed():
    return importlib.util.find_spec("ctrader_open_api") is not None


def _ctrader_endpoint_info():
    env = _get_ctrader_env_label()
    if env == "live":
        return "live.ctraderapi.com", 5035
    return "demo.ctraderapi.com", 5035


def _inspect_ctrader_open_api():
    result = {
        "package_imported": False,
        "package_file": "",
        "submodules": [],
        "tcp_protocol_classes": [],
        "tcp_protocol_file": "",
        "tcp_protocol_constructor_signature": "",
        "client_methods": [],
        "protobuf_methods": [],
        "currently_used_protocol": "",
        "protocol_created": False,
        "protocol_error": "",
        "factory_classes": [],
        "endpoint_constants": [],
        "descriptor_analysis": {},
        "matches": {
            "client": [],
            "application_auth_req": [],
            "account_auth_req": [],
            "get_account_list_by_access_token_req": [],
            "get_account_list_by_access_token_res": [],
            "symbols_list_req": [],
            "symbol_by_id_req": [],
            "symbol_by_id_res": [],
            "symbols_for_conversion_req": [],
            "symbol_category_list_req": [],
            "light_symbol": [],
            "symbol": [],
            "subscribe_spots_req": [],
            "subscribe_spots_res": [],
            "spot_event": [],
            "payload_type_2142": [],
        },
        "message": "",
    }

    try:
        sdk = importlib.import_module("ctrader_open_api")
        result["package_imported"] = True
        result["package_file"] = getattr(sdk, "__file__", "") or ""

        submodules = []
        if hasattr(sdk, "__path__"):
            for modinfo in pkgutil.walk_packages(sdk.__path__, sdk.__name__ + "."):
                submodules.append(modinfo.name)
        result["submodules"] = submodules[:500]

        target_names = {
            "client": ["Client", "OpenApiClient", "OpenApiConnectionClient"],
            "application_auth_req": ["ProtoOAApplicationAuthReq"],
            "account_auth_req": ["ProtoOAAccountAuthReq"],
            "get_account_list_by_access_token_req": ["ProtoOAGetAccountListByAccessTokenReq"],
            "get_account_list_by_access_token_res": ["ProtoOAGetAccountListByAccessTokenRes"],
            "symbols_list_req": ["ProtoOASymbolsListReq"],
            "symbol_by_id_req": ["ProtoOASymbolByIdReq"],
            "symbol_by_id_res": ["ProtoOASymbolByIdRes"],
            "symbols_for_conversion_req": ["ProtoOASymbolsForConversionReq"],
            "symbol_category_list_req": ["ProtoOASymbolCategoryListReq"],
            "light_symbol": ["ProtoOALightSymbol"],
            "symbol": ["ProtoOASymbol"],
            "subscribe_spots_req": ["ProtoOASubscribeSpotsReq"],
            "subscribe_spots_res": ["ProtoOASubscribeSpotsRes"],
            "spot_event": ["ProtoOASpotEvent"],
        }

        def scan_module(mod):
            hits = {key: [] for key in target_names}
            for key, names in target_names.items():
                for name in names:
                    if hasattr(mod, name):
                        hits[key].append(f"{mod.__name__}.{name}")
            return hits

        merged_hits = {key: [] for key in target_names}
        modules_to_scan = [sdk]
        for mod_name in submodules[:500]:
            try:
                modules_to_scan.append(importlib.import_module(mod_name))
            except Exception:
                continue

        for mod in modules_to_scan:
            hits = scan_module(mod)
            for key, values in hits.items():
                for value in values:
                    if value not in merged_hits[key]:
                        merged_hits[key].append(value)

        result["matches"] = merged_hits
        descriptor_targets = [
            "ProtoOASymbolsListReq",
            "ProtoOASymbolsListRes",
            "ProtoOASymbolByIdReq",
            "ProtoOASymbolByIdRes",
            "ProtoOALightSymbol",
            "ProtoOASymbol",
            "ProtoOAAssetListReq",
            "ProtoOAAssetListRes",
            "ProtoOASubscribeSpotsReq",
            "ProtoOASubscribeSpotsRes",
            "ProtoOASpotEvent",
        ]
        descriptor_analysis = {}
        try:
            pb2 = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        except Exception:
            pb2 = None
        try:
            model_pb2 = importlib.import_module("ctrader_open_api.messages.OpenApiModelMessages_pb2")
        except Exception:
            model_pb2 = None
        if pb2 is not None:
            for name in descriptor_targets:
                msg_cls = getattr(pb2, name, None) or getattr(model_pb2, name, None)
                if msg_cls is None:
                    continue
                try:
                    desc = msg_cls.DESCRIPTOR
                    fields = []
                    for field in desc.fields:
                        fields.append({
                            "name": field.name,
                            "number": field.number,
                            "type": field.type,
                            "label": field.label,
                            "message_type": field.message_type.full_name if field.message_type else "",
                            "enum_type": field.enum_type.full_name if field.enum_type else "",
                        })
                    descriptor_analysis[name] = {
                        "full_name": desc.full_name,
                        "fields": fields,
                    }
                except Exception as exc:
                    descriptor_analysis[name] = {
                        "full_name": name,
                        "fields": [],
                        "error": str(exc)[:240],
                    }
        result["descriptor_analysis"] = descriptor_analysis
        result["payload_type_enums"] = {
            "2142": "ProtoOASymbolsListRes",
            "subscribe_spots_res": "ProtoOASubscribeSpotsRes",
            "spot_event": "ProtoOASpotEvent",
        }
        result["matches"]["payload_type_2142"] = ["ProtoOASymbolsListRes"]
        try:
            tcp_mod = importlib.import_module("ctrader_open_api.tcpProtocol")
            result["tcp_protocol_file"] = getattr(tcp_mod, "__file__", "") or ""
            tcp_candidates = [name for name in dir(tcp_mod) if any(token in name for token in ("Tcp", "Protocol"))]
            result["tcp_protocol_classes"] = [f"{tcp_mod.__name__}.{name}" for name in tcp_candidates]
            protocol_cls = None
            for name in ("TcpProtocol", "Protocol", "TcpProtocolFactory", "TcpFactory"):
                if hasattr(tcp_mod, name):
                    protocol_cls = getattr(tcp_mod, name)
                    result["currently_used_protocol"] = f"{tcp_mod.__name__}.{name}"
                    break
            if protocol_cls is not None:
                try:
                    result["tcp_protocol_constructor_signature"] = str(inspect.signature(protocol_cls))
                except Exception:
                    result["tcp_protocol_constructor_signature"] = ""
                try:
                    result["protocol_created"] = True
                except Exception:
                    result["protocol_created"] = False
            result["factory_classes"] = [
                f"{tcp_mod.__name__}.{name}"
                for name in dir(tcp_mod)
                if any(token in name for token in ("Factory", "Protocol", "Client"))
            ]
        except Exception as exc:
            result["protocol_error"] = str(exc)[:240]

        for mod_name in ("ctrader_open_api.tcpProtocol", "ctrader_open_api.protobuf", "ctrader_open_api.client", "ctrader_open_api.endpoints"):
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue
            if mod_name.endswith("tcpProtocol"):
                result["tcp_protocol_classes"].extend([
                    f"{mod.__name__}.{name}" for name in dir(mod)
                    if any(token in name for token in ("Tcp", "Protocol", "Client"))
                ])
                for name in ("TcpProtocol", "Protocol", "TcpFactory", "TcpProtocolFactory"):
                    if hasattr(mod, name):
                        result["currently_used_protocol"] = f"{mod.__name__}.{name}"
                        try:
                            result["tcp_protocol_constructor_signature"] = str(inspect.signature(getattr(mod, name)))
                        except Exception:
                            result["tcp_protocol_constructor_signature"] = ""
                        break
            elif mod_name.endswith("client"):
                client_cls = getattr(mod, "Client", None)
                if client_cls is not None:
                    result["client_methods"] = [name for name in dir(client_cls) if not name.startswith("_")]
            elif mod_name.endswith("protobuf"):
                result["protobuf_methods"] = [name for name in dir(mod) if not name.startswith("_")]
            elif mod_name.endswith("endpoints"):
                result["endpoint_constants"] = [
                    f"{mod.__name__}.{name}" for name in dir(mod)
                    if name.isupper() or "ENDPOINT" in name.upper()
                ]
                if not result["endpoint_constants"]:
                    result["endpoint_constants"] = [f"{mod.__name__}.{name}" for name in dir(mod) if not name.startswith("_")]
        result["tcp_protocol_classes"] = sorted(list(dict.fromkeys(result["tcp_protocol_classes"])))[:200]
        result["client_methods"] = sorted(list(dict.fromkeys(result["client_methods"])))[:200]
        result["protobuf_methods"] = sorted(list(dict.fromkeys(result["protobuf_methods"])))[:200]
        result["factory_classes"] = sorted(list(dict.fromkeys(result["factory_classes"])))[:200]
        result["endpoint_constants"] = sorted(list(dict.fromkeys(result["endpoint_constants"])))[:200]
        result["message"] = "ok" if merged_hits["client"] else "package imported, no client class discovered"
    except Exception as exc:
        result["message"] = str(exc)[:240]

    return result


def _ctrader_class_candidates():
    resolved = {}
    try:
        import ctrader_open_api  # type: ignore
        resolved["Client"] = getattr(ctrader_open_api, "Client", None)
    except Exception:
        pass
    try:
        from ctrader_open_api import client as ctrader_client_mod  # type: ignore
        resolved.setdefault("Client", getattr(ctrader_client_mod, "Client", None))
    except Exception:
        pass
    try:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (  # type: ignore
            ProtoOAApplicationAuthReq,
            ProtoOAAccountAuthReq,
            ProtoOAGetAccountListByAccessTokenReq,
            ProtoOAGetAccountListByAccessTokenRes,
            ProtoOASymbolsListReq,
            ProtoOASubscribeSpotsReq,
            ProtoOASpotEvent,
        )
        resolved["ProtoOAApplicationAuthReq"] = ProtoOAApplicationAuthReq
        resolved["ProtoOAAccountAuthReq"] = ProtoOAAccountAuthReq
        resolved["ProtoOAGetAccountListByAccessTokenReq"] = ProtoOAGetAccountListByAccessTokenReq
        resolved["ProtoOAGetAccountListByAccessTokenRes"] = ProtoOAGetAccountListByAccessTokenRes
        resolved["ProtoOASymbolsListReq"] = ProtoOASymbolsListReq
        resolved["ProtoOASubscribeSpotsReq"] = ProtoOASubscribeSpotsReq
        resolved["ProtoOASpotEvent"] = ProtoOASpotEvent
        try:
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAAssetListReq, ProtoOAAssetListRes  # type: ignore
            resolved["ProtoOAAssetListReq"] = ProtoOAAssetListReq
            resolved["ProtoOAAssetListRes"] = ProtoOAAssetListRes
        except Exception:
            pass
    except Exception:
        pass
    return resolved


def _ctrader_required_sdk_classes():
    result = {
        "Client": None,
        "TcpProtocol": None,
        "Protobuf": None,
        "ProtoOAApplicationAuthReq": None,
        "ProtoOAAccountAuthReq": None,
        "ProtoOAGetAccountListByAccessTokenReq": None,
        "ProtoOASymbolsListReq": None,
        "ProtoOASymbolsListRes": None,
        "ProtoOASubscribeSpotsReq": None,
        "ProtoOASpotEvent": None,
    }
    candidates = _ctrader_class_candidates()
    for key in result:
        if candidates.get(key) is not None:
            result[key] = candidates.get(key)
    try:
        from ctrader_open_api.client import Client  # type: ignore
        result["Client"] = result["Client"] or Client
    except Exception:
        pass
    try:
        from ctrader_open_api.tcpProtocol import TcpProtocol  # type: ignore
        result["TcpProtocol"] = result["TcpProtocol"] or TcpProtocol
    except Exception:
        pass
    try:
        from ctrader_open_api.protobuf import Protobuf  # type: ignore
        result["Protobuf"] = result["Protobuf"] or Protobuf
    except Exception:
        pass
    try:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (  # type: ignore
            ProtoOAApplicationAuthReq,
            ProtoOAAccountAuthReq,
            ProtoOAGetAccountListByAccessTokenReq,
            ProtoOASymbolsListReq,
            ProtoOASymbolsListRes,
            ProtoOASubscribeSpotsReq,
        )
        result["ProtoOAApplicationAuthReq"] = result["ProtoOAApplicationAuthReq"] or ProtoOAApplicationAuthReq
        result["ProtoOAAccountAuthReq"] = result["ProtoOAAccountAuthReq"] or ProtoOAAccountAuthReq
        result["ProtoOAGetAccountListByAccessTokenReq"] = result["ProtoOAGetAccountListByAccessTokenReq"] or ProtoOAGetAccountListByAccessTokenReq
        result["ProtoOASymbolsListReq"] = result["ProtoOASymbolsListReq"] or ProtoOASymbolsListReq
        result["ProtoOASymbolsListRes"] = result["ProtoOASymbolsListRes"] or ProtoOASymbolsListRes
        result["ProtoOASubscribeSpotsReq"] = result["ProtoOASubscribeSpotsReq"] or ProtoOASubscribeSpotsReq
    except Exception:
        pass
    try:
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOASpotEvent  # type: ignore
        result["ProtoOASpotEvent"] = result["ProtoOASpotEvent"] or ProtoOASpotEvent
    except Exception:
        try:
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASpotEvent  # type: ignore
            result["ProtoOASpotEvent"] = result["ProtoOASpotEvent"] or ProtoOASpotEvent
        except Exception:
            pass
    return result


def _run_ctrader_session(load_symbols=True, load_assets=False):
    runtime = _get_ctrader_runtime()
    classes = _ctrader_required_sdk_classes()
    session = {
        "runtime": runtime,
        "classes": classes,
        "missing_classes": [name for name, cls in classes.items() if cls is None],
        "symbol_map": dict(CTRADER_SYMBOL_MAP),
        "raw_symbol_list": [],
        "client": None,
        "account_auth_ok": False,
    }
    if load_symbols and not CTRADER_SYMBOL_MAP:
        try:
            _ensure_ctrader_symbol_cache(runtime)
            session["symbol_map"] = dict(CTRADER_SYMBOL_MAP)
        except Exception:
            pass
    return session


def _run_ctrader_session_with_client(load_symbols=True, load_assets=False, keep_client_open=False):
    session = _run_ctrader_session(load_symbols=load_symbols, load_assets=load_assets)
    runtime = session["runtime"]
    classes = session["classes"]
    client_cls = classes.get("Client")
    app_req_cls = classes.get("ProtoOAApplicationAuthReq")
    account_list_req_cls = classes.get("ProtoOAGetAccountListByAccessTokenReq")
    account_req_cls = classes.get("ProtoOAAccountAuthReq")
    if not all([client_cls, app_req_cls, account_list_req_cls, account_req_cls]):
        session["missing_classes"] = [name for name, cls in {
            "Client": client_cls,
            "ProtoOAApplicationAuthReq": app_req_cls,
            "ProtoOAGetAccountListByAccessTokenReq": account_list_req_cls,
            "ProtoOAAccountAuthReq": account_req_cls,
        }.items() if cls is None]
        return session

    try:
        host, port = _ctrader_endpoint_info()
        reactor_ok, _ = _ctrader_ensure_reactor_running()
        if not reactor_ok:
            return session
        protocol_obj, _, _ = _ctrader_create_protocol(host, port, use_instance=False)
        if protocol_obj is None:
            return session
        client = _ctrader_init_client(client_cls, host, port, protocol_obj)
        session["client"] = client
        connected_event = threading.Event()

        def connected_callback(*args, **kwargs):
            connected_event.set()

        if hasattr(client, "setConnectedCallback"):
            try:
                client.setConnectedCallback(connected_callback)
            except Exception:
                pass
        client.startService()
        connected_event.wait(4)
        if not connected_event.is_set():
            return session

        app_req = app_req_cls()
        if hasattr(app_req, "clientId"):
            app_req.clientId = runtime["client_id"]
        if hasattr(app_req, "clientSecret"):
            app_req.clientSecret = runtime["client_secret"]
        _ctrader_send_request_and_wait(client, app_req, "application", timeout=6)

        account_list_req = account_list_req_cls()
        if hasattr(account_list_req, "accessToken"):
            account_list_req.accessToken = runtime["access_token"]
        account_list_msg, _ = _ctrader_send_request_and_wait(client, account_list_req, "account", timeout=6)
        if account_list_msg is not None:
            _extract_account_list(_extract_message_payload(account_list_msg))

        account_req = account_req_cls()
        if hasattr(account_req, "ctidTraderAccountId"):
            account_req.ctidTraderAccountId = int(runtime["account_id"])
        if hasattr(account_req, "accessToken"):
            account_req.accessToken = runtime["access_token"]
        _ctrader_send_request_and_wait(client, account_req, "account", timeout=6)
        session["account_auth_ok"] = True
        session["client"] = client
        session["session_return_keys"] = list(session.keys())
        session["session_client_present_before_return"] = "client" in session and session["client"] is not None
        session["session_client_type_before_return"] = type(session.get("client")).__name__ if session.get("client") else ""
        if not keep_client_open:
            _ctrader_safe_stop_service(client)
        return session
    except Exception:
        return session


def _ctrader_init_client(client_cls, host, port, protocol=None):
    attempts = [
        lambda: client_cls(host, port, protocol),
        lambda: client_cls(host=host, port=port, protocol=protocol),
        lambda: client_cls(host, port, protocol, None),
        lambda: client_cls(host, port),
        lambda: client_cls(host=host, port=port),
        lambda: client_cls(host, port, True),
    ]
    last_exc = None
    for attempt in attempts:
        try:
            return attempt()
        except Exception as exc:
            last_exc = exc
    raise last_exc or RuntimeError("client_init_failed")


def _ctrader_attach_callback(client, event_name, callback):
    if hasattr(client, event_name):
        attr = getattr(client, event_name)
        try:
            if callable(attr):
                attr(callback)
                return True
        except Exception:
            pass
    setter_name = f"set{event_name[:1].upper()}{event_name[1:]}"
    if hasattr(client, setter_name):
        setter = getattr(client, setter_name)
        try:
            setter(callback)
            return True
        except Exception:
            pass
    return False


def _ctrader_send_request(client, request, timeout=10):
    """
    Best-effort request/response bridge for the installed ctrader_open_api SDK.
    Returns the first response-like object or raises on timeout/error.
    """
    response_queue = Queue()
    stop_event = threading.Event()

    def on_message(message=None, *args, **kwargs):
        payload = message if message is not None else (args[0] if args else None)
        response_queue.put(payload)
        stop_event.set()

    attached = False
    for cb_name in (
        "messageReceived",
        "onMessageReceived",
        "message_received",
        "message",
    ):
        attached = _ctrader_attach_callback(client, cb_name, on_message) or attached

    send_attempts = [
        lambda: client.send(request),
        lambda: client.sendMessage(request),
        lambda: client.sendMessageToServer(request),
        lambda: client.execute(request),
    ]
    last_exc = None
    sent = False
    for attempt in send_attempts:
        try:
            result = attempt()
            sent = True
            if result is not None and result is not True:
                response_queue.put(result)
                stop_event.set()
            break
        except Exception as exc:
            last_exc = exc

    if not sent:
        raise last_exc or RuntimeError("request_send_failed")

    try:
        return response_queue.get(timeout=timeout)
    except Empty:
        if stop_event.is_set():
            return None
        raise TimeoutError("request timeout")


def _ctrader_send_request_and_wait(client, request, expected_token, timeout=6):
    """
    Send a protobuf request through the SDK client and wait for a matching response.
    Returns (message, error_text).
    """
    response_queue = Queue()
    last_error = {"value": ""}

    def on_message(message=None, *args, **kwargs):
        payload = message if message is not None else (args[0] if args else None)
        response_queue.put(payload)

    callback_attached = False
    for cb_name in ("setMessageReceivedCallback", "messageReceived", "onMessageReceived"):
        if hasattr(client, cb_name):
            try:
                getattr(client, cb_name)(on_message)
                callback_attached = True
                break
            except Exception as exc:
                last_error["value"] = str(exc)[:240]

    if not callback_attached:
        return None, last_error["value"] or "message callback unavailable"

    try:
        send_result = client.send(request)
        if send_result is not None and send_result is not True:
            response_queue.put(send_result)
    except Exception as exc:
        return None, str(exc)[:240]

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            message = response_queue.get(timeout=0.2)
        except Empty:
            continue
        if message is None:
            continue
        if expected_token.lower() in _ctrader_message_name(message).lower():
            return message, ""
    return None, "timeout"


def _ctrader_run_auth_chain(client, runtime):
    """
    Read-only auth chain after connection:
    ApplicationAuth -> AccountAuth -> SymbolsList.
    """
    diagnostics = {
        "application_auth": "failed",
        "account_auth": "failed",
        "account_list_request": "not_tested",
        "accounts_found": 0,
        "accounts": [],
        "account_id_match": False,
        "symbols_request": "failed",
        "symbols_found": 0,
        "symbols": [],
        "outer_payload_type": "",
        "decoded_payload_type": "",
        "decoded_payload_fields": [],
        "symbols_field_name": "",
        "symbols_response_type": "",
        "symbols_response_fields": [],
        "raw_symbols_count_candidates": [],
        "payload_type": "",
        "extracted_message_type": "",
        "extracted_fields": [],
        "outer_payload_type": "",
        "decoded_payload_type": "",
        "decoded_payload_fields": [],
        "symbols_field_name": "",
        "first_symbol_type": "",
        "first_symbol_fields": [],
        "first_symbol_dict": {},
        "asset_list_request": "not_tested",
        "assets_found": 0,
        "assets": [],
        "asset_response_fields": [],
        "asset_payload_type": "",
        "variants": [],
        "message": "",
    }

    classes = _ctrader_class_candidates()
    app_req_cls = classes.get("ProtoOAApplicationAuthReq")
    account_req_cls = classes.get("ProtoOAAccountAuthReq")
    account_list_req_cls = classes.get("ProtoOAGetAccountListByAccessTokenReq")
    symbols_req_cls = classes.get("ProtoOASymbolsListReq")
    asset_req_cls = classes.get("ProtoOAAssetListReq")
    if not all([app_req_cls, account_req_cls, account_list_req_cls, symbols_req_cls, asset_req_cls]):
        diagnostics["message"] = "required auth classes not found"
        return diagnostics

    account_id_int = int(runtime["account_id"])

    try:
        from twisted.internet import reactor, defer  # type: ignore
    except Exception as exc:
        diagnostics["message"] = f"{type(exc).__name__}: {str(exc)[:240]}"
        return diagnostics

    timeout_seconds = 6
    done = threading.Event()
    final = {"value": diagnostics}

    def _extract_message_payload(msg):
        try:
            return msg.message if hasattr(msg, "message") else msg
        except Exception:
            return msg

    def _message_to_dict(msg):
        try:
            from google.protobuf.json_format import MessageToDict  # type: ignore
            return MessageToDict(msg, preserving_proto_field_name=True)
        except Exception:
            pass
        try:
            if hasattr(msg, "ListFields"):
                data = {}
                for field_desc, value in msg.ListFields():
                    data[field_desc.name] = value
                return data
        except Exception:
            pass
        return {}

    def _finish(res):
        final["value"] = res
        done.set()
        return res

    def _fail(err, stage):
        diagnostics["message"] = f"{stage} failed: {getattr(err, 'getErrorMessage', lambda: str(err))()}"
        done.set()
        return err

    def _extract_symbols(msg):
        diagnostics["symbols_response_type"] = f"{type(msg).__module__}.{type(msg).__name__}"
        diagnostics["outer_payload_type"] = str(getattr(msg, "payloadType", "") or getattr(msg, "payload_type", "") or "")
        if hasattr(msg, "ListFields"):
            try:
                diagnostics["symbols_response_fields"] = [field_desc.name for field_desc, _ in msg.ListFields()]
            except Exception:
                diagnostics["symbols_response_fields"] = []
        payload_bytes = getattr(msg, "payload", None)
        if payload_bytes is None:
            payload_bytes = _extract_message_payload(msg)
        diagnostics["payload_type"] = f"{type(payload_bytes).__module__}.{type(payload_bytes).__name__}"
        diagnostics["extracted_message_type"] = f"{type(msg).__module__}.{type(msg).__name__}"
        diagnostics["symbol_decoded_payload_type"] = ""
        diagnostics["symbol_decoded_payload_fields"] = []
        diagnostics["symbol_field_name"] = ""
        decoded = None
        try:
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASymbolsListRes  # type: ignore
            if isinstance(payload_bytes, (bytes, bytearray)):
                decoded = ProtoOASymbolsListRes()
                decoded.ParseFromString(payload_bytes)
                diagnostics["symbol_decoded_payload_type"] = "ProtoOASymbolsListRes"
            elif hasattr(payload_bytes, "ListFields"):
                decoded = payload_bytes
                diagnostics["symbol_decoded_payload_type"] = f"{type(decoded).__module__}.{type(decoded).__name__}"
        except Exception as exc:
            diagnostics["symbol_decoded_payload_type"] = ""
            diagnostics["message"] = f"symbols decode failed: {type(exc).__name__}: {str(exc)[:160]}"

        if decoded is not None and hasattr(decoded, "ListFields"):
            try:
                diagnostics["symbol_decoded_payload_fields"] = [field_desc.name for field_desc, _ in decoded.ListFields()]
            except Exception:
                diagnostics["symbol_decoded_payload_fields"] = []

        symbol_items = []
        diagnostics["symbol_field_name"] = "symbol"
        target_msg = decoded
        if target_msg is not None and hasattr(target_msg, "ListFields"):
            try:
                for field_desc, value in target_msg.ListFields():
                    if field_desc.name == "symbol" and isinstance(value, list):
                        symbol_items = value
                        diagnostics["raw_symbols_count_candidates"].append({"symbol": len(value)})
                        break
                    if isinstance(value, list) and not symbol_items:
                        diagnostics["raw_symbols_count_candidates"].append({field_desc.name: len(value)})
            except Exception:
                pass
        if target_msg is not None and hasattr(target_msg, "symbol"):
            try:
                symbol_items = list(getattr(target_msg, "symbol") or [])
            except Exception:
                symbol_items = []
        diagnostics["symbols_request"] = "ok"
        diagnostics["symbols_found"] = len(symbol_items)
        diagnostics["symbols"] = []
        all_symbols = []
        try:
            from google.protobuf.json_format import MessageToDict  # type: ignore
        except Exception:
            MessageToDict = None
        for item in symbol_items:
            item_dict = None
            if MessageToDict is not None:
                try:
                    item_dict = MessageToDict(item, preserving_proto_field_name=True)
                except Exception:
                    item_dict = None
            if item_dict is None:
                item_dict = _message_to_dict(item)
            all_symbols.append(item_dict)
        diagnostics["symbols"] = all_symbols[:100]
        if symbol_items:
            first_symbol = symbol_items[0]
            diagnostics["first_symbol_type"] = f"{type(first_symbol).__module__}.{type(first_symbol).__name__}"
            if hasattr(first_symbol, "ListFields"):
                try:
                    diagnostics["first_symbol_fields"] = [field_desc.name for field_desc, _ in first_symbol.ListFields()]
                except Exception:
                    diagnostics["first_symbol_fields"] = []
            try:
                from google.protobuf.json_format import MessageToDict  # type: ignore
                diagnostics["first_symbol_dict"] = MessageToDict(first_symbol, preserving_proto_field_name=True)
            except Exception:
                diagnostics["first_symbol_dict"] = {}
        try:
            if all_symbols:
                _store_ctrader_symbol_map(all_symbols)
        except Exception:
            pass
        diagnostics["message"] = ""
        return diagnostics

    def _extract_assets(msg):
        diagnostics["asset_payload_type"] = f"{type(msg).__module__}.{type(msg).__name__}"
        if hasattr(msg, "ListFields"):
            try:
                diagnostics["asset_response_fields"] = [field_desc.name for field_desc, _ in msg.ListFields()]
            except Exception:
                diagnostics["asset_response_fields"] = []
        payload_bytes = getattr(msg, "payload", None)
        if payload_bytes is None:
            payload_bytes = _extract_message_payload(msg)
        diagnostics["asset_payload_type"] = f"{type(payload_bytes).__module__}.{type(payload_bytes).__name__}"
        diagnostics["asset_raw_payload_bytes_length"] = len(payload_bytes) if isinstance(payload_bytes, (bytes, bytearray)) else 0
        diagnostics["asset_decoded_payload_type"] = ""
        diagnostics["asset_decoded_payload_fields"] = []
        diagnostics["asset_field_name"] = ""

        assets = []
        decoded = None
        try:
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAAssetListRes  # type: ignore
            if isinstance(payload_bytes, (bytes, bytearray)):
                decoded = ProtoOAAssetListRes()
                decoded.ParseFromString(payload_bytes)
                diagnostics["asset_decoded_payload_type"] = "ProtoOAAssetListRes"
            elif hasattr(payload_bytes, "ListFields"):
                decoded = payload_bytes
                diagnostics["asset_decoded_payload_type"] = f"{type(decoded).__module__}.{type(decoded).__name__}"
        except Exception as exc:
            diagnostics["message"] = f"asset list decode failed: {type(exc).__name__}: {str(exc)[:160]}"

        if decoded is not None and hasattr(decoded, "ListFields"):
            try:
                diagnostics["asset_decoded_payload_fields"] = [field_desc.name for field_desc, _ in decoded.ListFields()]
            except Exception:
                diagnostics["asset_decoded_payload_fields"] = []

        if decoded is not None and hasattr(decoded, "asset"):
            try:
                assets = list(getattr(decoded, "asset") or [])
                diagnostics["asset_field_name"] = "asset"
            except Exception:
                assets = []
        elif decoded is not None and hasattr(decoded, "ListFields"):
            try:
                for field_desc, value in decoded.ListFields():
                    if isinstance(value, list):
                        assets = value
                        diagnostics["asset_field_name"] = field_desc.name
                        break
            except Exception:
                assets = []
        diagnostics["asset_list_request"] = "ok"
        diagnostics["assets_found"] = len(assets)
        diagnostics["assets"] = []
        for item in assets[:50]:
            try:
                from google.protobuf.json_format import MessageToDict  # type: ignore
                diagnostics["assets"].append(MessageToDict(item, preserving_proto_field_name=True))
            except Exception:
                diagnostics["assets"].append(_message_to_dict(item))
        return diagnostics

    def _extract_account_list(msg):
        diagnostics["account_list_request"] = "ok"
        diagnostics["account_list_response_type"] = f"{type(msg).__module__}.{type(msg).__name__}"
        if hasattr(msg, "ListFields"):
            try:
                diagnostics["account_list_response_fields"] = [field_desc.name for field_desc, _ in msg.ListFields()]
            except Exception:
                diagnostics["account_list_response_fields"] = []
        payload_bytes = getattr(msg, "payload", None)
        if payload_bytes is None:
            payload_bytes = _extract_message_payload(msg)
        diagnostics["account_list_payload_type"] = f"{type(payload_bytes).__module__}.{type(payload_bytes).__name__}"
        diagnostics["raw_account_payload_bytes_length"] = len(payload_bytes) if isinstance(payload_bytes, (bytes, bytearray)) else 0
        diagnostics["raw_account_response_dict"] = {}
        decoded = None
        try:
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetAccountListByAccessTokenRes  # type: ignore
            if isinstance(payload_bytes, (bytes, bytearray)):
                decoded = ProtoOAGetAccountListByAccessTokenRes()
                decoded.ParseFromString(payload_bytes)
                diagnostics["account_list_decoded_type"] = "ProtoOAGetAccountListByAccessTokenRes"
            elif hasattr(payload_bytes, "ListFields"):
                decoded = payload_bytes
                diagnostics["account_list_decoded_type"] = f"{type(decoded).__module__}.{type(decoded).__name__}"
        except Exception as exc:
            diagnostics["account_list_decoded_type"] = ""
            diagnostics["message"] = f"account list decode failed: {type(exc).__name__}: {str(exc)[:160]}"
        try:
            if decoded is not None:
                diagnostics["raw_account_response_dict"] = _message_to_dict(decoded)
        except Exception:
            diagnostics["raw_account_response_dict"] = {}

        accounts = []
        if decoded is not None:
            raw_accounts = []
            if hasattr(decoded, "ctidTraderAccount"):
                try:
                    raw_accounts = list(getattr(decoded, "ctidTraderAccount") or [])
                except Exception:
                    raw_accounts = []
            elif hasattr(decoded, "ListFields"):
                try:
                    for field_desc, value in decoded.ListFields():
                        if field_desc.name == "ctidTraderAccount" and isinstance(value, list):
                            raw_accounts = value
                            break
                except Exception:
                    raw_accounts = []
            diagnostics["accounts_found"] = len(raw_accounts)
            for acc in raw_accounts[:10]:
                accounts.append({
                    "ctidTraderAccountId": str(getattr(acc, "ctidTraderAccountId", "") or ""),
                    "isLive": bool(getattr(acc, "isLive", False)),
                    "traderLogin": str(getattr(acc, "traderLogin", "") or ""),
                    "brokerName": str(getattr(acc, "brokerName", "") or ""),
                })
            diagnostics["accounts"] = accounts
            diagnostics["account_id_match"] = any(
                str(getattr(acc, "ctidTraderAccountId", "") or "") == str(account_id_int)
                for acc in raw_accounts
            )
        else:
            diagnostics["accounts_found"] = 0
            diagnostics["accounts"] = []
            diagnostics["account_id_match"] = False
        return diagnostics

    def _build_account_list_req():
        req = account_list_req_cls()
        if hasattr(req, "accessToken"):
            req.accessToken = runtime["access_token"]
        return req

    def do_account_auth(_=None):
        req = account_req_cls()
        if hasattr(req, "ctidTraderAccountId"):
            req.ctidTraderAccountId = account_id_int
        if hasattr(req, "accessToken"):
            req.accessToken = runtime["access_token"]
        d2 = defer.maybeDeferred(client.send, req)
        def _ok(_msg):
            diagnostics["account_auth"] = "ok"

            def _asset_req():
                req = asset_req_cls()
                if hasattr(req, "ctidTraderAccountId"):
                    req.ctidTraderAccountId = account_id_int
                return req

            d_asset = defer.maybeDeferred(client.send, _asset_req())

            def _asset_ok(msg_asset):
                _extract_assets(_extract_message_payload(msg_asset))
                return msg_asset

            def _asset_bad(err):
                diagnostics["asset_list_request"] = "failed"
                diagnostics["message"] = f"asset list failed: {getattr(err, 'getErrorMessage', lambda: str(err))()}"
                return err

            d_asset.addCallbacks(_asset_ok, _asset_bad)
            d_asset.addErrback(_asset_bad)

            def _symbols_req(include_archived):
                req = symbols_req_cls()
                if hasattr(req, "ctidTraderAccountId"):
                    req.ctidTraderAccountId = account_id_int
                if hasattr(req, "includeArchivedSymbols"):
                    req.includeArchivedSymbols = include_archived
                return req

            def _collect(res):
                diagnostics["variants"].append({
                    "include_archived": res.get("include_archived", False),
                    "symbols_found": res.get("symbols_found", 0),
                    "first_symbol_fields": res.get("first_symbol_fields", []),
                    "first_symbol_dict": res.get("first_symbol_dict", {}),
                    "symbols": res.get("symbols", []),
                })
                if res.get("include_archived") is True:
                    diagnostics["symbols_request"] = res.get("symbols_request", "failed")
                    diagnostics["symbols_found"] = res.get("symbols_found", 0)
                    diagnostics["symbols"] = res.get("symbols", [])
                    diagnostics["decoded_payload_type"] = "ProtoOASymbolsListRes"
                    diagnostics["symbols_field_name"] = "symbol"
                    diagnostics["first_symbol_type"] = res.get("first_symbol_type", "")
                    diagnostics["first_symbol_fields"] = res.get("first_symbol_fields", [])
                    diagnostics["first_symbol_dict"] = res.get("first_symbol_dict", {})
                diagnostics["asset_list_request"] = diagnostics.get("asset_list_request", "not_tested")
                return res

            def _run_one(include_archived):
                req = _symbols_req(include_archived)
                d3 = defer.maybeDeferred(client.send, req)

                def _ok_symbol(msg):
                    extracted = _extract_message_payload(msg)
                    res = _extract_symbols(extracted)
                    res["include_archived"] = include_archived
                    return res

                d3.addCallbacks(_ok_symbol, lambda err: _fail(err, "symbols request"))
                d3.addErrback(lambda err: _fail(err, "symbols request"))
                d3.addCallbacks(_collect, lambda err: _fail(err, "symbols request"))
                return d3

            _run_one(False)
            return _run_one(True)
        def _bad(err):
            diagnostics["account_auth"] = "failed"
            return _fail(err, "account auth")
        d2.addCallbacks(_ok, _bad)
        return d2

    def do_account_list(_=None):
        d_list = defer.maybeDeferred(client.send, _build_account_list_req())

        def _list_ok(msg_list):
            _extract_account_list(_extract_message_payload(msg_list))
            if not diagnostics["account_id_match"]:
                diagnostics["message"] = "CTRADER_ACCOUNT_ID not found in authorized account list"
                diagnostics["account_auth"] = "not_tested"
                diagnostics["symbols_request"] = "not_tested"
                diagnostics["asset_list_request"] = "not_tested"
                return diagnostics
            return do_account_auth()

        def _list_bad(err):
            diagnostics["account_list_request"] = "failed"
            return _fail(err, "account list")

        d_list.addCallbacks(_list_ok, _list_bad)
        d_list.addErrback(_list_bad)
        return d_list

    def do_application_auth(_=None):
        req = app_req_cls()
        if hasattr(req, "clientId"):
            req.clientId = runtime["client_id"]
        if hasattr(req, "clientSecret"):
            req.clientSecret = runtime["client_secret"]
        d1 = defer.maybeDeferred(client.send, req)
        def _ok(msg):
            diagnostics["application_auth"] = "ok"
            return do_account_list(_extract_message_payload(msg))
        def _bad(err):
            diagnostics["application_auth"] = "failed"
            return _fail(err, "application auth")
        d1.addCallbacks(_ok, _bad)
        return d1

    try:
        d = defer.maybeDeferred(do_application_auth)
        d.addBoth(lambda _: _finish(diagnostics))
        reactor.callLater(timeout_seconds, lambda: (not done.is_set()) and _finish({**diagnostics, "message": "timeout"}))
        done.wait(timeout_seconds + 1)
        return final["value"]
    except Exception as exc:
        diagnostics["message"] = f"{type(exc).__name__}: {str(exc)[:240]}"
        return diagnostics


def _ctrader_safe_stop_service(client):
    for method_name in ("stopService", "stop", "disconnect"):
        if hasattr(client, method_name):
            try:
                getattr(client, method_name)()
                return True
            except Exception:
                continue
    return False


def _ctrader_reactor_status():
    status = {
        "reactor_imported": False,
        "reactor_running": None,
        "reactor_stopped": None,
        "reactor_type": "",
    }
    try:
        from twisted.internet import reactor  # type: ignore
        status["reactor_imported"] = True
        status["reactor_type"] = reactor.__class__.__name__
        status["reactor_running"] = bool(getattr(reactor, "running", False))
        status["reactor_stopped"] = bool(getattr(reactor, "stopped", False))
    except Exception as exc:
        status["reactor_type"] = f"unavailable: {type(exc).__name__}"
    return status


_CTRADER_REACTOR_THREAD = None
_CTRADER_REACTOR_LOCK = threading.Lock()


def _ctrader_ensure_reactor_running():
    try:
        from twisted.internet import reactor  # type: ignore
    except Exception as exc:
        return False, f"reactor import failed: {type(exc).__name__}"

    if getattr(reactor, "running", False):
        return True, "running"

    with _CTRADER_REACTOR_LOCK:
        global _CTRADER_REACTOR_THREAD
        if _CTRADER_REACTOR_THREAD and _CTRADER_REACTOR_THREAD.is_alive():
            return True, "thread_alive"

        def _run():
            try:
                reactor.run(installSignalHandlers=False)
            except Exception:
                pass

        _CTRADER_REACTOR_THREAD = threading.Thread(target=_run, name="ctrader-reactor", daemon=True)
        _CTRADER_REACTOR_THREAD.start()

    for _ in range(30):
        if getattr(reactor, "running", False):
            return True, "started"
        time.sleep(0.1)

    return False, "reactor start timeout"


def _ctrader_create_protocol(host, port, use_instance=False):
    try:
        tcp_mod = importlib.import_module("ctrader_open_api.tcpProtocol")
    except Exception as exc:
        return None, "", f"{type(exc).__name__}: {str(exc)[:160]}"

    for name in ("TcpProtocol", "Protocol", "TcpFactory", "TcpProtocolFactory"):
        candidate = getattr(tcp_mod, name, None)
        if candidate is None:
            continue
        protocol_used = f"{tcp_mod.__name__}.{name}"
        try:
            sig = inspect.signature(candidate)
        except Exception:
            sig = None
        attempts = []
        if sig and len(sig.parameters) == 0:
            attempts.append(lambda: candidate())
        attempts.extend([
            lambda: candidate(host, port),
            lambda: candidate(host=host, port=port),
            lambda: candidate(host, port, None),
        ])
        if use_instance:
            instance_attempts = [lambda: candidate(), lambda: candidate(host, port), lambda: candidate(host=host, port=port)]
        else:
            instance_attempts = [lambda: candidate, lambda: candidate]
        last_exc = None
        for attempt in (instance_attempts + attempts):
            try:
                return attempt(), protocol_used, ""
            except Exception as exc:
                last_exc = exc
        return None, protocol_used, f"{type(last_exc).__name__}: {str(last_exc)[:160]}" if last_exc else "protocol creation failed"
    return None, "", "tcp protocol class not found"


def _ctrader_message_name(message):
    if message is None:
        return ""
    if hasattr(message, "DESCRIPTOR"):
        return message.DESCRIPTOR.name
    return message.__class__.__name__


def _ctrader_symbol_from_message(message):
    symbol_id = getattr(message, "symbolId", None) or getattr(message, "ctidTraderSymbolId", None) or getattr(message, "id", None)
    symbol_name = getattr(message, "symbolName", None) or getattr(message, "name", None)
    base_asset_id = getattr(message, "baseAssetId", None)
    quote_asset_id = getattr(message, "quoteAssetId", None)
    return {
        "symbol_id": str(symbol_id) if symbol_id is not None else "",
        "symbol_name": str(symbol_name) if symbol_name is not None else "",
        "base_asset_id": str(base_asset_id) if base_asset_id is not None else "",
        "quote_asset_id": str(quote_asset_id) if quote_asset_id is not None else "",
    }


def _ctrader_message_to_dict(message):
    try:
        from google.protobuf.json_format import MessageToDict  # type: ignore
        return MessageToDict(message, preserving_proto_field_name=True)
    except Exception:
        pass
    try:
        if hasattr(message, "ListFields"):
            data = {}
            for field_desc, value in message.ListFields():
                data[field_desc.name] = value
            return data
    except Exception:
        pass
    return {}


def _ctrader_message_ok(message, expected_token):
    name = _ctrader_message_name(message).lower()
    if expected_token.lower() not in name:
        return False
    for attr in ("errorCode", "errorMessage", "error", "status"):
        value = getattr(message, attr, None)
        if value not in (None, "", 0, "0"):
            if attr == "status" and str(value).lower() in ("ok", "success", "online"):
                return True
            if attr != "status":
                return False
    return True


def _ctrader_wait_for_spot_quote(client, subscribe_request, timeout=10, diagnostics=None):
    """
    Send a spot subscription and wait for a spot event.
    Returns (quote_dict, meta_dict).
    """
    meta = {
        "subscribe_request_sent": False,
        "subscribe_response_received": False,
        "spot_event_received": False,
        "received_payload_types": [],
        "received_message_types": [],
        "raw_received_count": 0,
        "timeout_seconds": timeout,
        "error": "",
    }
    spot_event_holder = {"value": None}
    stop_event = threading.Event()

    def _record_message(message=None, *args, **kwargs):
        payload = message if message is not None else (args[0] if args else kwargs.get("message"))
        if payload is None:
            return None
        meta["raw_received_count"] += 1
        meta["received_message_types"].append(_ctrader_message_name(payload))
        meta["received_payload_types"].append(type(getattr(payload, "payload", payload)).__name__)
        payload_type = str(getattr(payload, "payloadType", "") or getattr(payload, "payload_type", "") or "")
        if payload_type:
            meta["received_payload_types"].append(payload_type)

        name = _ctrader_message_name(payload).lower()
        if "subscribe" in name and "spot" in name:
            meta["subscribe_response_received"] = True
        if "spot" in name:
            meta["spot_event_received"] = True
            spot_event_holder["value"] = payload
            stop_event.set()
        return None

    attached = False
    for cb_name in ("setMessageReceivedCallback", "messageReceived", "onMessageReceived", "message_received", "message"):
        attached = _ctrader_attach_callback(client, cb_name, _record_message) or attached

    try:
        send_result = client.send(subscribe_request)
        meta["subscribe_request_sent"] = True
        if send_result is not None and send_result is not True:
            _record_message(send_result)
    except Exception as exc:
        meta["error"] = str(exc)[:240]
        if diagnostics is not None:
            diagnostics.update(meta)
        return None, meta

    deadline = time.time() + timeout
    while time.time() < deadline and not stop_event.is_set():
        time.sleep(0.05)

    if spot_event_holder["value"] is None:
        meta["error"] = "timeout"
        if diagnostics is not None:
            diagnostics.update(meta)
        return None, meta

    quote = _ctrader_extract_spot_quote(spot_event_holder["value"])
    if diagnostics is not None:
        diagnostics.update(meta)
    return quote, meta


def _ctrader_collect_inbound_messages(client, duration=10):
    collected = []
    stop_event = threading.Event()

    def on_message(message=None, *args, **kwargs):
        payload = message if message is not None else (args[0] if args else kwargs.get("message"))
        if payload is None:
            return None
        collected.append({
            "payload_type": str(getattr(payload, "payloadType", "") or getattr(payload, "payload_type", "") or ""),
            "message_type": _ctrader_message_name(payload),
            "client_msg_id": str(getattr(payload, "clientMsgId", "") or getattr(payload, "client_msg_id", "") or ""),
            "payload": payload,
        })
        return None

    attached = False
    for cb_name in ("setMessageReceivedCallback", "messageReceived", "onMessageReceived", "message_received", "message"):
        attached = _ctrader_attach_callback(client, cb_name, on_message) or attached

    if not attached:
        return collected

    deadline = time.time() + duration
    while time.time() < deadline and not stop_event.is_set():
        time.sleep(0.05)
    return collected


def _ctrader_sdk_diagnostics():
    package_installed = _ctrader_package_installed()
    runtime = _get_ctrader_runtime()
    host, port = _ctrader_endpoint_info()
    diagnostics = {
        "package_installed": package_installed,
        "env": runtime["env"],
        "host": host,
        "port": port,
        "application_auth": "not_tested",
        "account_auth": "not_tested",
        "account_list_request": "not_tested",
        "accounts_found": 0,
        "accounts": [],
        "account_id_match": False,
        "symbols_request": "not_tested",
        "symbols_found": 0,
        "message": "",
    }

    if not package_installed:
        diagnostics["application_auth"] = "failed"
        diagnostics["account_auth"] = "failed"
        diagnostics["symbols_request"] = "failed"
        diagnostics["message"] = "ctrader_open_api not installed; pip install ctrader_open_api"
        return diagnostics

    client_id = runtime["client_id"]
    client_secret = runtime["client_secret"]
    access_token = runtime["access_token"]
    account_id = runtime["account_id"]

    if not (client_id and client_secret):
        diagnostics["application_auth"] = "failed"
        diagnostics["message"] = "client credentials missing"
        return diagnostics

    if not access_token:
        diagnostics["application_auth"] = "ok"
        diagnostics["account_auth"] = "failed"
        diagnostics["message"] = "access token missing"
        return diagnostics

    if not account_id:
        diagnostics["application_auth"] = "ok"
        diagnostics["account_auth"] = "failed"
        diagnostics["message"] = "account id missing"
        return diagnostics

    try:
        import importlib
        import pkgutil

        sdk = importlib.import_module("ctrader_open_api")

        def find_attr(*names):
            for name in names:
                if hasattr(sdk, name):
                    return getattr(sdk, name)
            for modinfo in getattr(sdk, "__path__", []):
                pass
            for _, mod_name, _ in pkgutil.walk_packages(sdk.__path__, sdk.__name__ + "."):
                try:
                    mod = importlib.import_module(mod_name)
                except Exception:
                    continue
                for name in names:
                    if hasattr(mod, name):
                        return getattr(mod, name)
            return None

        client_cls = find_attr("Client", "OpenApiClient", "OpenApiConnectionClient")
        if client_cls is None:
            diagnostics["message"] = "ctrader_open_api installed but client class not found"
            diagnostics["application_auth"] = "failed"
            diagnostics["account_auth"] = "failed"
            diagnostics["symbols_request"] = "failed"
            return diagnostics

        diagnostics["message"] = "ctrader_open_api client class discovered; SDK wiring depends on runtime API"
        diagnostics["application_auth"] = "failed"
        diagnostics["account_auth"] = "failed"
        diagnostics["symbols_request"] = "failed"
        return diagnostics
    except Exception as exc:
        diagnostics["message"] = f"ctrader_open_api diagnostic error: {str(exc)[:240]}"
        diagnostics["application_auth"] = "failed"
        diagnostics["account_auth"] = "failed"
        diagnostics["symbols_request"] = "failed"
        return diagnostics


def _fetch_ctrader_quote(symbol, runtime):
    normalized_symbol, _ = _normalize_ctrader_symbol(symbol)
    if not _ctrader_package_installed():
        return _build_trading_response(normalized_symbol, "offline", "ctrader_open_api not installed")

    session = _run_ctrader_session(load_symbols=True, load_assets=False)
    runtime = session["runtime"]
    if runtime["env"] not in ("demo", "live"):
        return _build_trading_response(normalized_symbol, "offline", "environment demo/live falsch")
    mapped = get_mapped_symbol(normalized_symbol, runtime=runtime, ensure_cache=True)
    symbol_id = mapped["symbol_id"]
    mapped_response = _build_trading_response(normalized_symbol, "mapped", "symbol mapped, quote subscription pending")
    mapped_response.update({
        "symbol_id": symbol_id,
        "display_name": mapped.get("display_name") or mapped_response["display_name"],
        "description": mapped.get("description") or mapped_response["description"],
        "label": mapped.get("description") or mapped_response["label"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    if not symbol_id:
        return mapped_response
    host, port = _ctrader_endpoint_info()
    classes = session["classes"]
    client_cls = classes.get("Client")
    app_auth_cls = classes.get("ProtoOAApplicationAuthReq")
    account_list_cls = classes.get("ProtoOAGetAccountListByAccessTokenReq")
    account_auth_cls = classes.get("ProtoOAAccountAuthReq")
    subscribe_spots_cls = classes.get("ProtoOASubscribeSpotsReq")
    if not all([client_cls, app_auth_cls, account_list_cls, account_auth_cls, subscribe_spots_cls]):
        return mapped_response

    reactor_ok, _ = _ctrader_ensure_reactor_running()
    if not reactor_ok:
        return mapped_response

    protocol_obj, _, _ = _ctrader_create_protocol(host, port, use_instance=False)
    if protocol_obj is None:
        return mapped_response

    client = _ctrader_init_client(client_cls, host, port, protocol_obj)
    connected_event = threading.Event()
    last_spot = {"value": None}

    def connected_callback(*args, **kwargs):
        connected_event.set()

    def message_received_callback(*args, **kwargs):
        payload = args[0] if args else kwargs.get("message")
        if payload is None:
            return None
        name = _ctrader_message_name(payload).lower()
        if "spot" in name:
            last_spot["value"] = payload
        return None

    if hasattr(client, "setConnectedCallback"):
        try:
            client.setConnectedCallback(connected_callback)
        except Exception:
            pass
    if hasattr(client, "setMessageReceivedCallback"):
        try:
            client.setMessageReceivedCallback(message_received_callback)
        except Exception:
            pass

    try:
        client.startService()
    except Exception:
        _ctrader_safe_stop_service(client)
        return mapped_response

    connected_event.wait(4)
    if not connected_event.is_set():
        _ctrader_safe_stop_service(client)
        return mapped_response

    try:
        app_req = app_auth_cls()
        if hasattr(app_req, "clientId"):
            app_req.clientId = runtime["client_id"]
        if hasattr(app_req, "clientSecret"):
            app_req.clientSecret = runtime["client_secret"]
        _ctrader_send_request_and_wait(client, app_req, "application", timeout=6)

        account_list_req = account_list_cls()
        if hasattr(account_list_req, "accessToken"):
            account_list_req.accessToken = runtime["access_token"]
        account_list_msg, _ = _ctrader_send_request_and_wait(client, account_list_req, "account", timeout=6)
        if account_list_msg is not None:
            _extract_account_list(_extract_message_payload(account_list_msg))

        account_auth_req = account_auth_cls()
        if hasattr(account_auth_req, "ctidTraderAccountId"):
            account_auth_req.ctidTraderAccountId = int(runtime["account_id"])
        if hasattr(account_auth_req, "accessToken"):
            account_auth_req.accessToken = runtime["access_token"]
        _ctrader_send_request_and_wait(client, account_auth_req, "account", timeout=6)

        subscribe_req = subscribe_spots_cls()
        if hasattr(subscribe_req, "ctidTraderAccountId"):
            subscribe_req.ctidTraderAccountId = int(runtime["account_id"])
        if hasattr(subscribe_req, "symbolId"):
            try:
                subscribe_req.symbolId.append(int(symbol_id))
            except Exception:
                try:
                    subscribe_req.symbolId.extend([int(symbol_id)])
                except Exception:
                    pass
        elif hasattr(subscribe_req, "symbol_ids"):
            subscribe_req.symbol_ids = [int(symbol_id)]
        elif hasattr(subscribe_req, "symbolIdList"):
            subscribe_req.symbolIdList = [int(symbol_id)]
        elif hasattr(subscribe_req, "symbols"):
            try:
                subscribe_req.symbols.append(int(symbol_id))
            except Exception:
                pass

        quote, meta_diag = _ctrader_wait_for_spot_quote(client, subscribe_req, timeout=10)
        if quote is None:
            return mapped_response

        response = _build_trading_response(normalized_symbol, "online", "live quote")
        response.update({
            "symbol_id": symbol_id,
            "display_name": meta.get("display_name") or response["display_name"],
            "description": meta.get("description") or response["description"],
            "label": meta.get("description") or response["label"],
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "spread": quote.get("spread"),
            "last_price": quote.get("last_price"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return response
    finally:
        _ctrader_safe_stop_service(client)


def _ctrader_symbol_key_from_quote(message, fallback_symbol=""):
    meta = _ctrader_symbol_from_message(message)
    symbol_name = (meta.get("symbol_name") or fallback_symbol or "").strip().upper()
    if symbol_name:
        normalized, _ = _normalize_ctrader_symbol(symbol_name)
        return normalized
    symbol_id = meta.get("symbol_id") or ""
    if symbol_id:
        for key, value in CTRADER_SYMBOL_CATALOG.items():
            if str(value.get("symbol_id")) == str(symbol_id):
                symbol_name = value.get("symbolName") or value.get("symbol_name") or ""
                if symbol_name:
                    normalized, _ = _normalize_ctrader_symbol(symbol_name)
                    return normalized
    return fallback_symbol.strip().upper()


def _ctrader_update_quote_cache(symbol_key, quote, message=None):
    if not symbol_key:
        return
    symbol_key = symbol_key.strip().upper()
    payload = {
        "symbol": symbol_key,
        "symbol_id": str((quote or {}).get("symbol_id") or _resolve_ctrader_symbol_id(symbol_key) or ""),
        "bid": (quote or {}).get("bid"),
        "ask": (quote or {}).get("ask"),
        "spread": (quote or {}).get("spread"),
        "last_price": (quote or {}).get("last_price"),
        "raw_bid": (quote or {}).get("raw_bid"),
        "raw_ask": (quote or {}).get("raw_ask"),
        "raw_spread": (quote or {}).get("raw_spread"),
        "raw_last_price": (quote or {}).get("raw_last_price"),
        "price_scale": (quote or {}).get("price_scale"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "message": "live quote",
    }
    if message is not None:
        try:
            payload["raw"] = _ctrader_message_to_dict(message)
        except Exception:
            payload["raw"] = {}
    with CTRADER_STREAM_LOCK:
        CTRADER_QUOTE_CACHE[symbol_key] = payload
        CTRADER_STREAM_STATUS["last_event_at"] = payload["updated_at"]


def _ctrader_symbol_name_from_id(symbol_id):
    symbol_id = str(symbol_id or "").strip()
    reverse = {
        "1": "EURUSD",
        "2": "GBPUSD",
        "41": "XAUUSD",
        "101": "BTCUSD",
        "102": "ETHUSD",
    }
    return reverse.get(symbol_id, "")


def _ctrader_stream_worker():
    runtime = _get_ctrader_runtime()
    host, port = _ctrader_endpoint_info()
    watchlist = ["XAUUSD", "EURUSD", "BTCUSD", "US500", "GER40"]
    for sym in watchlist:
        try:
            get_mapped_symbol(sym, runtime=runtime, ensure_cache=True)
        except Exception:
            pass

    with CTRADER_STREAM_LOCK:
        CTRADER_STREAM_STATUS["status"] = "starting"
        CTRADER_STREAM_STATUS["started_at"] = datetime.now(timezone.utc).isoformat()
        CTRADER_STREAM_STATUS["connected"] = False
        CTRADER_STREAM_STATUS["subscribed_symbols"] = []
        CTRADER_STREAM_STATUS["subscribed_symbol_ids"] = []
        CTRADER_STREAM_STATUS["last_error"] = ""
        CTRADER_STREAM_STATUS["last_event_at"] = ""
        CTRADER_STREAM_STATUS["last_message_at"] = ""
        CTRADER_STREAM_STATUS["last_payload_type"] = ""
        CTRADER_STREAM_STATUS["last_message_fields"] = []
        CTRADER_STREAM_STATUS["last_spot_event_fields"] = []
        CTRADER_STREAM_STATUS["last_spot_event_dict"] = {}
        CTRADER_STREAM_STATUS["last_spot_symbol_id"] = ""
        CTRADER_STREAM_STATUS["callback_invoked_count"] = 0
        CTRADER_STREAM_STATUS["received_payload_types"] = []
        CTRADER_STREAM_STATUS["subscribe_requests_sent"] = 0
        CTRADER_STREAM_STATUS["subscribe_responses_received"] = 0
        CTRADER_STREAM_STATUS["subscribe_errors"] = 0
        CTRADER_STREAM_STATUS["spot_event_count"] = 0

    if runtime.get("env") not in ("demo", "live"):
        with CTRADER_STREAM_LOCK:
            CTRADER_STREAM_STATUS["status"] = "error"
            CTRADER_STREAM_STATUS["last_error"] = "environment demo/live falsch"
        return

    classes = _ctrader_required_sdk_classes()
    client_cls = classes.get("Client")
    app_auth_cls = classes.get("ProtoOAApplicationAuthReq")
    account_auth_cls = classes.get("ProtoOAAccountAuthReq")
    subscribe_spots_cls = classes.get("ProtoOASubscribeSpotsReq")
    if not all([client_cls, app_auth_cls, account_auth_cls, subscribe_spots_cls]):
        with CTRADER_STREAM_LOCK:
            CTRADER_STREAM_STATUS["status"] = "error"
            CTRADER_STREAM_STATUS["last_error"] = "required stream classes missing"
        return

    reactor_ok, _ = _ctrader_ensure_reactor_running()
    if not reactor_ok:
        with CTRADER_STREAM_LOCK:
            CTRADER_STREAM_STATUS["status"] = "error"
            CTRADER_STREAM_STATUS["last_error"] = "reactor not running"
        return

    protocol_obj, _, proto_err = _ctrader_create_protocol(host, port, use_instance=False)
    if protocol_obj is None:
        with CTRADER_STREAM_LOCK:
            CTRADER_STREAM_STATUS["status"] = "error"
            CTRADER_STREAM_STATUS["last_error"] = proto_err or "protocol creation failed"
        return

    stale_seconds = 90

    while not CTRADER_STREAM_STOP_EVENT.is_set():
        try:
            client = _ctrader_init_client(client_cls, host, port, protocol_obj)
        except Exception as exc:
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["status"] = "error"
                CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
            return

        connected_event = threading.Event()
        subscribe_ids = []

        def on_connected(*args, **kwargs):
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["connected"] = True
            connected_event.set()

        def on_disconnected(*args, **kwargs):
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["connected"] = False

        def on_message(*args):
            message = args[-1] if args else None
            if message is None:
                return None
            try:
                payload_type = str(getattr(message, "payloadType", "") or getattr(message, "payload_type", "") or "")
                with CTRADER_STREAM_LOCK:
                    CTRADER_STREAM_STATUS["callback_invoked_count"] += 1
                    if payload_type:
                        CTRADER_STREAM_STATUS["received_payload_types"].append(payload_type)
                    CTRADER_STREAM_STATUS["last_message_at"] = datetime.now(timezone.utc).isoformat()
                    CTRADER_STREAM_STATUS["last_payload_type"] = payload_type
                    try:
                        CTRADER_STREAM_STATUS["last_message_fields"] = [field.name for field, value in message.ListFields()]
                    except Exception:
                        CTRADER_STREAM_STATUS["last_message_fields"] = []
                if payload_type == "2142":
                    try:
                        payload_bytes = getattr(message, "payload", None)
                        if payload_bytes is None and hasattr(message, "message"):
                            payload_bytes = getattr(message, "message")
                        if isinstance(payload_bytes, (bytes, bytearray)):
                            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAErrorRes  # type: ignore
                            error_res = ProtoOAErrorRes()
                            error_res.ParseFromString(payload_bytes)
                            error_code = str(getattr(error_res, "errorCode", "") or "")
                            error_desc = str(getattr(error_res, "description", "") or "")
                            with CTRADER_STREAM_LOCK:
                                CTRADER_STREAM_STATUS["last_error"] = (error_code + ": " + error_desc).strip(": ")[:240]
                    except Exception as exc:
                        with CTRADER_STREAM_LOCK:
                            CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
                    return None

                spot_payload_bytes = None
                decoded_spot = None
                if payload_type == "2131" or "spot" in _ctrader_message_name(message).lower():
                    payload_bytes = getattr(message, "payload", None)
                    if isinstance(payload_bytes, (bytes, bytearray)):
                        spot_payload_bytes = payload_bytes
                    elif hasattr(message, "message") and isinstance(getattr(message, "message", None), (bytes, bytearray)):
                        spot_payload_bytes = getattr(message, "message")
                    if spot_payload_bytes is not None:
                        try:
                            spot_cls = _ctrader_required_sdk_classes().get("ProtoOASpotEvent")
                            if spot_cls is not None:
                                decoded_spot = spot_cls()
                                decoded_spot.ParseFromString(spot_payload_bytes)
                        except Exception as exc:
                            with CTRADER_STREAM_LOCK:
                                CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
                if decoded_spot is None and "spot" not in _ctrader_message_name(message).lower():
                    return None

                quote_source = decoded_spot if decoded_spot is not None else message
                quote = _ctrader_extract_spot_quote(quote_source)
                symbol_id = ""
                if decoded_spot is not None:
                    symbol_id = str(getattr(decoded_spot, "symbolId", "") or getattr(decoded_spot, "ctidTraderSymbolId", "") or "")
                    try:
                        with CTRADER_STREAM_LOCK:
                            CTRADER_STREAM_STATUS["spot_event_count"] += 1
                            CTRADER_STREAM_STATUS["last_spot_symbol_id"] = symbol_id
                            CTRADER_STREAM_STATUS["last_spot_event_fields"] = [field.name for field, value in decoded_spot.ListFields()]
                            CTRADER_STREAM_STATUS["last_spot_event_dict"] = _ctrader_message_to_dict(decoded_spot)
                    except Exception:
                        pass
                symbol_key = _ctrader_symbol_name_from_id(symbol_id) if symbol_id else _ctrader_symbol_key_from_quote(quote_source)
                quote["symbol_id"] = symbol_id or quote.get("symbol_id")
                _ctrader_update_quote_cache(symbol_key, quote, message=decoded_spot if decoded_spot is not None else message)
            except Exception as exc:
                with CTRADER_STREAM_LOCK:
                    CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
            return None

        if hasattr(client, "setConnectedCallback"):
            try:
                client.setConnectedCallback(on_connected)
            except Exception:
                pass
        if hasattr(client, "setDisconnectedCallback"):
            try:
                client.setDisconnectedCallback(on_disconnected)
            except Exception:
                pass
        if hasattr(client, "setMessageReceivedCallback"):
            try:
                client.setMessageReceivedCallback(on_message)
            except Exception as exc:
                with CTRADER_STREAM_LOCK:
                    CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]

        try:
            client.startService()
        except Exception as exc:
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["status"] = "error"
                CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
            _ctrader_safe_stop_service(client)
            return

        if not connected_event.wait(10):
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["status"] = "error"
                CTRADER_STREAM_STATUS["last_error"] = "connect timeout"
            _ctrader_safe_stop_service(client)
            return

        try:
            app_req = app_auth_cls()
            if hasattr(app_req, "clientId"):
                app_req.clientId = runtime["client_id"]
            if hasattr(app_req, "clientSecret"):
                app_req.clientSecret = runtime["client_secret"]
            _ctrader_send_request_and_wait(client, app_req, "application", timeout=6)

            account_req = account_auth_cls()
            if hasattr(account_req, "ctidTraderAccountId"):
                account_req.ctidTraderAccountId = int(runtime["account_id"])
            if hasattr(account_req, "accessToken"):
                account_req.accessToken = runtime["access_token"]
            _ctrader_send_request_and_wait(client, account_req, "account", timeout=6)
        except Exception as exc:
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["status"] = "error"
                CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
            _ctrader_safe_stop_service(client)
            return

        if hasattr(client, "setMessageReceivedCallback"):
            try:
                client.setMessageReceivedCallback(on_message)
            except Exception as exc:
                with CTRADER_STREAM_LOCK:
                    CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]

        watchlist_ids = []
        for sym in watchlist:
            mapped = get_mapped_symbol(sym, runtime=runtime, ensure_cache=True)
            if mapped.get("symbol_id"):
                try:
                    watchlist_ids.append(int(mapped["symbol_id"]))
                except Exception:
                    pass
        subscribe_ids = list(watchlist_ids)

        try:
            sub_req = subscribe_spots_cls()
            if hasattr(sub_req, "ctidTraderAccountId"):
                sub_req.ctidTraderAccountId = int(runtime["account_id"])
            if hasattr(sub_req, "symbolId"):
                try:
                    sub_req.symbolId.extend(watchlist_ids)
                except Exception:
                    for sid in watchlist_ids:
                        try:
                            sub_req.symbolId.append(int(sid))
                        except Exception:
                            pass
            if hasattr(sub_req, "subscribeToSpotTimestamp"):
                try:
                    sub_req.subscribeToSpotTimestamp = int(time.time() * 1000)
                except Exception:
                    pass
            if hasattr(sub_req, "clientMsgId"):
                sub_req.clientMsgId = f"stream_subscribe_{int(time.time() * 1000)}"
            d = client.send(sub_req)
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["status"] = "running"
                CTRADER_STREAM_STATUS["subscribed_symbols"] = [str(s) for s in watchlist]
                CTRADER_STREAM_STATUS["subscribed_symbol_ids"] = [int(s) for s in subscribe_ids]
                CTRADER_STREAM_STATUS["subscribe_requests_sent"] += 1
            if hasattr(d, "addCallbacks"):
                def _on_ok(result):
                    with CTRADER_STREAM_LOCK:
                        CTRADER_STREAM_STATUS["subscribe_responses_received"] += 1
                        if result is not None:
                            try:
                                result_payload_type = str(getattr(result, "payloadType", "") or getattr(result, "payload_type", "") or "")
                                if result_payload_type:
                                    CTRADER_STREAM_STATUS["last_payload_type"] = result_payload_type
                                try:
                                    CTRADER_STREAM_STATUS["last_message_fields"] = [field.name for field, value in result.ListFields()]
                                except Exception:
                                    pass
                            except Exception:
                                pass
                    return result

                def _on_err(failure):
                    with CTRADER_STREAM_LOCK:
                        CTRADER_STREAM_STATUS["subscribe_errors"] += 1
                        CTRADER_STREAM_STATUS["last_error"] = str(failure)[:240]
                    return failure

                try:
                    d.addCallbacks(_on_ok, _on_err)
                except Exception as exc:
                    with CTRADER_STREAM_LOCK:
                        CTRADER_STREAM_STATUS["subscribe_errors"] += 1
                        CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
        except Exception as exc:
            with CTRADER_STREAM_LOCK:
                CTRADER_STREAM_STATUS["status"] = "error"
                CTRADER_STREAM_STATUS["last_error"] = str(exc)[:240]
            _ctrader_safe_stop_service(client)
            return

        while not CTRADER_STREAM_STOP_EVENT.wait(2):
            with CTRADER_STREAM_LOCK:
                current_status = CTRADER_STREAM_STATUS.get("status")
                connected = bool(CTRADER_STREAM_STATUS.get("connected"))
                last_event_at = CTRADER_STREAM_STATUS.get("last_event_at") or ""
                last_message_at = CTRADER_STREAM_STATUS.get("last_message_at") or ""
            if current_status == "stopping":
                break
            if not connected:
                with CTRADER_STREAM_LOCK:
                    CTRADER_STREAM_STATUS["last_error"] = "stream disconnected, restarting"
                break
            if last_event_at:
                try:
                    last_event_dt = datetime.fromisoformat(last_event_at.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - last_event_dt).total_seconds() > stale_seconds:
                        with CTRADER_STREAM_LOCK:
                            CTRADER_STREAM_STATUS["last_error"] = "stale spot stream, restarting"
                        break
                except Exception:
                    with CTRADER_STREAM_LOCK:
                        CTRADER_STREAM_STATUS["last_error"] = "invalid spot timestamp, restarting"
                    break
            elif last_message_at:
                try:
                    last_message_dt = datetime.fromisoformat(last_message_at.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - last_message_dt).total_seconds() > stale_seconds:
                        with CTRADER_STREAM_LOCK:
                            CTRADER_STREAM_STATUS["last_error"] = "no spot events, restarting"
                        break
                except Exception:
                    with CTRADER_STREAM_LOCK:
                        CTRADER_STREAM_STATUS["last_error"] = "invalid message timestamp, restarting"
                    break

        _ctrader_safe_stop_service(client)
        if CTRADER_STREAM_STOP_EVENT.is_set():
            break
        with CTRADER_STREAM_LOCK:
            CTRADER_STREAM_STATUS["connected"] = False
            if CTRADER_STREAM_STATUS.get("status") != "error":
                CTRADER_STREAM_STATUS["status"] = "restarting"
        time.sleep(2)

    with CTRADER_STREAM_LOCK:
        if CTRADER_STREAM_STATUS.get("status") not in ("error", "restarting"):
            CTRADER_STREAM_STATUS["status"] = "stopped"


def _ctrader_start_stream_thread():
    global CTRADER_STREAM_THREAD
    with CTRADER_STREAM_LOCK:
        if CTRADER_STREAM_THREAD is not None and CTRADER_STREAM_THREAD.is_alive():
            return CTRADER_STREAM_THREAD, False
        CTRADER_STREAM_STOP_EVENT.clear()
        CTRADER_STREAM_THREAD = threading.Thread(target=_ctrader_stream_worker, name="ctrader-stream", daemon=True)
        CTRADER_STREAM_THREAD.start()
        return CTRADER_STREAM_THREAD, True


def _ensure_ctrader_symbol_cache(runtime):
    if CTRADER_SYMBOL_MAP:
        return True
    host, port = _ctrader_endpoint_info()
    classes = _ctrader_class_candidates()
    client_cls = classes.get("Client")
    if client_cls is None:
        return False

    reactor_ok, _ = _ctrader_ensure_reactor_running()
    if not reactor_ok:
        return False

    protocol_obj, _, _ = _ctrader_create_protocol(host, port, use_instance=False)
    if protocol_obj is None:
        return False

    client = _ctrader_init_client(client_cls, host, port, protocol_obj)
    connected_event = threading.Event()

    def connected_callback(*args, **kwargs):
        connected_event.set()

    if hasattr(client, "setConnectedCallback"):
        try:
            client.setConnectedCallback(connected_callback)
        except Exception:
            pass

    try:
        client.startService()
    except Exception:
        _ctrader_safe_stop_service(client)
        return False

    connected_event.wait(4)
    if not connected_event.is_set():
        _ctrader_safe_stop_service(client)
        return False

    try:
        _ctrader_run_auth_chain(client, runtime)
        return bool(CTRADER_SYMBOL_MAP)
    finally:
        _ctrader_safe_stop_service(client)


def _ctrader_symbol_catalog_matches(symbols, terms):
    matches = []
    for item in symbols or []:
        text = " ".join([
            str(item.get("symbolName", "")),
            str(item.get("symbol_name", "")),
            str(item.get("display_name", "")),
            str(item.get("description", "")),
        ]).upper()
        compact = text.replace(" ", "").replace("/", "").replace("-", "").replace(".", "")
        for term in terms:
            term_upper = str(term).upper()
            term_compact = term_upper.replace(" ", "").replace("/", "").replace("-", "").replace(".", "")
            if term_upper in text or term_compact in compact:
                matches.append(item)
                break
    return matches

HERMES_START_TIME = time.time()
HERMES_ENV_PATH = r"\\wsl$\Ubuntu\home\ramses\.hermes\.env"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/pixel")
def pixel():
    return render_template("index_pixel.html")


@app.route("/static/img/hermes_dashboard_reference.png")
def pixel_reference_image():
    reference_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reference", "Hermes Dashboard.png")
    return send_file(reference_path, conditional=True)


@app.route("/api/system")
def api_system():
    system_uptime_seconds = int(time.time() - psutil.boot_time())
    hermes_uptime_seconds = int(time.time() - HERMES_START_TIME)

    disk = shutil.disk_usage("C:\\")
    disk_used_percent = round((disk.used / disk.total) * 100, 1)

    return jsonify({
        "status": "online",
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": disk_used_percent,
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        "system_uptime_seconds": system_uptime_seconds,
        "system_uptime_text": format_uptime(system_uptime_seconds),
        "hermes_uptime_seconds": hermes_uptime_seconds,
        "hermes_uptime_text": format_uptime(hermes_uptime_seconds),
        "model": "DeepSeek Flash",
        "provider": "OpenRouter"
    })


@app.route("/api/openrouter")
def api_openrouter():
    api_key = get_openrouter_key()

    if not api_key:
        return jsonify({
            "status": "error",
            "message": "OPENROUTER_API_KEY nicht gefunden",
            "provider": "OpenRouter",
            "model": OPENROUTER_MODEL,
            "credit": None
        }), 500

    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/credits",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "provider": "OpenRouter",
                "model": OPENROUTER_MODEL,
                "http_status": response.status_code,
                "message": response.text[:300],
                "credit": None
            }), 500

        data = response.json()
        credits = data.get("data", {})
        total = credits.get("total_credits")
        usage = credits.get("total_usage")

        return jsonify({
            "status": "online",
            "provider": "OpenRouter",
            "model": OPENROUTER_MODEL,
            "credit": total,
            "usage": usage,
            "remaining": total - usage if total is not None and usage is not None else None
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "provider": "OpenRouter",
            "model": OPENROUTER_MODEL,
            "message": str(error),
            "credit": None
        }), 500

@app.route("/api/usage")
def api_usage():
    return api_openrouter()


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}

    user_text = (
        data.get("message")
        or data.get("text")
        or data.get("prompt")
        or data.get("input")
        or ""
    ).strip()

    if not user_text:
        return jsonify({
            "status": "error",
            "message": "Keine Eingabe erhalten"
        }), 400

    try:
        cmd = [
            "wsl",
            "-d", "Ubuntu",
            "-u", "ramses",
            "--",
            "/home/ramses/.local/bin/hermes",
            "-z",
            user_text
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": result.stderr.strip() or "Hermes-Fehler"
            }), 500

        answer = result.stdout.strip()

        return jsonify({
            "status": "online",
            "answer": answer,
            "response": answer,
            "result": answer
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500


@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.get_json(silent=True) or {}
    text = data.get("text") or data.get("message") or ""

    return jsonify({
        "status": "ok",
        "text": text
    })


@app.route("/api/business-scout")
def api_business_scout():
    api_key = get_openrouter_key()

    if not api_key:
        return jsonify({
            "status": "error",
            "message": "OPENROUTER_API_KEY nicht gefunden"
        }), 500

    prompt = """
Du bist der Business Scout des RentenPilot-Projekts.

Aufgabe:
Erstelle 10 priorisierte Content-Ideen für RentenPilot.

Fokus:
- Rente
- früher in Rente
- GdB 50
- Schwerbehindertenrente
- Rentensteuer
- Rentenbescheid
- häufige Fehler
- Social-Media-taugliche Themen

Ausgabe bitte kompakt und strukturiert:

1. Titel
2. Warum relevant
3. Formatvorschlag: Blog / TikTok / YouTube Short / FAQ
4. Priorität: hoch / mittel / niedrig
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "RentenPilot Command Center"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Du bist Hermes, Chief AI Officer des RentenPilot-Projekts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.4,
                "max_tokens": 1200
            },
            timeout=60
        )

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "http_status": response.status_code,
                "message": response.text[:1000]
            }), 500

        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        return jsonify({
            "status": "online",
            "agent": "Business Scout",
            "model": OPENROUTER_MODEL,
            "result": answer
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "agent": "Business Scout",
            "message": str(error)
        }), 500


def get_openrouter_key():
    values = dotenv_values(HERMES_ENV_PATH)
    return values.get("OPENROUTER_API_KEY")


def format_uptime(seconds):
    days = seconds // 86400
    seconds %= 86400
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60

    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@app.route("/api/hermes_status")
def api_hermes_status():
    return jsonify({
        "version": "1.0.0-beta",
        "status": "Online",
        "agents": ["Hermes Core", "Business Scout", "Code", "Web"],
        "skills": ["File System", "Code Exec", "Web Search", "API"]
    })


@app.route("/api/trading/env_status")
def api_trading_env_status():
    return jsonify(_get_env_status())



@app.route("/api/trading/assets")
def api_trading_assets():
    """Return the list of tradeable assets (read-only metadata)."""
    return jsonify({
        "status": "ok",
        "mode": "read_only",
        "assets": [
            {"symbol": sym, **meta}
            for sym, meta in TRADING_ASSETS.items()
        ]
    })


@app.route("/api/trading/symbols")
def api_trading_symbols():
    runtime = _get_ctrader_runtime()
    account_present = bool(runtime.get("account_id"))
    base = {
        "status": "offline",
        "provider": "cTrader",
        "account_id_present": account_present,
        "symbols_found": 0,
        "symbols": [],
        "message": "",
        "endpoint_used": "",
        "http_status": None,
    }

    if not account_present:
        base["message"] = "account id missing"
        return jsonify(base)

    if not runtime.get("access_token"):
        base["message"] = "token invalid"
        return jsonify(base)

    last_error = None
    try:
        _ensure_ctrader_symbol_cache(runtime)
    except Exception as exc:
        last_error = str(exc)[:240]

    symbols = []
    if CTRADER_SYMBOL_CATALOG:
        symbols = [dict(item) for item in CTRADER_SYMBOL_CATALOG.values()]
    elif CTRADER_SYMBOL_MAP:
        symbols = [
            {
                "symbol_id": str(symbol_id),
                "symbolName": str(symbol_name),
                "symbol_name": str(symbol_name),
                "display_name": str(symbol_name),
                "description": str(symbol_name),
            }
            for symbol_name, symbol_id in CTRADER_SYMBOL_MAP.items()
        ]

    base["endpoint_used"] = "ctrader_symbol_cache"
    base["http_status"] = 200 if symbols else None
    base["symbols_found"] = len(symbols)
    base["symbols"] = symbols
    base["status"] = "online" if symbols else "offline"
    base["message"] = "" if symbols else (last_error or "symbol cache empty")
    return jsonify(base)


@app.route("/api/trading/sdk_inspect")
def api_trading_sdk_inspect():
    return jsonify(_inspect_ctrader_open_api())


@app.route("/api/trading/ctrader_diagnostics")
def api_trading_ctrader_diagnostics():
    runtime = _get_ctrader_runtime()
    host, port = _ctrader_endpoint_info()
    result = {
        "package_installed": _ctrader_package_installed(),
        "env": runtime["env"],
        "host": host,
        "port": port,
        "connection_target": f"{host}:{port}",
        "endpoint_source": "",
        "protocol_used": "",
        "protocol_created": False,
        "protocol_error": "",
        "client_import_path": "",
        "client_class_found": False,
        "client_constructor_signature": "",
        "variations": [],
        "reactor_status": _ctrader_reactor_status(),
        "application_auth": "not_tested",
        "account_auth": "not_tested",
        "account_list_request": "not_tested",
        "accounts_found": 0,
        "accounts": [],
        "account_id_match": False,
        "symbols_request": "not_tested",
        "symbols_found": 0,
        "symbols": [],
        "symbols_response_type": "",
        "symbols_response_fields": [],
        "raw_symbols_count_candidates": [],
        "payload_type": "",
        "extracted_message_type": "",
        "extracted_fields": [],
        "outer_payload_type": "",
        "decoded_payload_type": "",
        "decoded_payload_fields": [],
        "symbols_field_name": "",
        "first_symbol_type": "",
        "first_symbol_fields": [],
        "first_symbol_dict": {},
        "asset_list_request": "not_tested",
        "assets_found": 0,
        "assets": [],
        "asset_response_fields": [],
        "asset_payload_type": "",
        "message": "",
    }

    if not result["package_installed"]:
        result["application_auth"] = "failed"
        result["account_auth"] = "failed"
        result["symbols_request"] = "failed"
        result["message"] = "ctrader_open_api not installed; pip install ctrader_open_api"
        return jsonify(result)

    required = {
        "client_id": runtime["client_id"],
        "client_secret": runtime["client_secret"],
        "access_token": runtime["access_token"],
        "account_id": runtime["account_id"],
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        result["message"] = "missing env: " + ", ".join(missing)
        result["application_auth"] = "failed"
        result["account_auth"] = "failed"
        result["symbols_request"] = "failed"
        return jsonify(result)

    try:
        classes = _ctrader_class_candidates()
        client_cls = classes.get("Client")
        if client_cls is None:
            result["client_import_path"] = ""
            result["client_class_found"] = False
            result["message"] = "client class not found"
            return jsonify(result)

        result["client_class_found"] = True
        try:
            result["client_import_path"] = f"{client_cls.__module__}.{client_cls.__name__}"
        except Exception:
            result["client_import_path"] = str(client_cls)
        try:
            result["client_constructor_signature"] = str(inspect.signature(client_cls))
        except Exception:
            result["client_constructor_signature"] = ""

        reactor_ok, reactor_note = _ctrader_ensure_reactor_running()
        result["reactor_status"] = _ctrader_reactor_status()
        result["reactor_status"]["startup_note"] = reactor_note
        if not reactor_ok:
            result["message"] = reactor_note
            result["protocol_error"] = reactor_note
            return jsonify(result)

        try:
            protocol_class, protocol_class_used, protocol_class_error = _ctrader_create_protocol(host, port, use_instance=False)
            protocol_instance, protocol_instance_used, protocol_instance_error = _ctrader_create_protocol(host, port, use_instance=True)
        except Exception as exc:
            result["protocol_error"] = str(exc)[:240]
            return jsonify(result)

        variants = [
            ("class", protocol_class, protocol_class_used, protocol_class_error),
            ("instance", protocol_instance, protocol_instance_used, protocol_instance_error),
        ]

        for protocol_mode, protocol_obj, protocol_used, protocol_error in variants:
            variant_result = {
                "protocol_mode": protocol_mode,
                "protocol_used": protocol_used,
                "protocol_created": protocol_obj is not None,
                "client_created": False,
                "service_started": False,
                "connected": False,
                "error": protocol_error or "",
                "application_auth": "not_tested",
                "account_auth": "not_tested",
                "symbols_request": "not_tested",
                "symbols_found": 0,
                "symbols": [],
            }

            if protocol_obj is None:
                result["variations"].append(variant_result)
                continue

            result["protocol_used"] = protocol_used
            result["protocol_created"] = True
            result["protocol_error"] = protocol_error or ""
            result["endpoint_source"] = "ctrader_open_api.endpoints"

            try:
                client = _ctrader_init_client(client_cls, host, port, protocol_obj)
                variant_result["client_created"] = True
            except Exception as exc:
                variant_result["error"] = str(exc)[:240]
                result["variations"].append(variant_result)
                continue

            connected_event = threading.Event()
            def connected_callback(*args, **kwargs):
                variant_result["connected"] = True
                connected_event.set()

            def message_received_callback(*args, **kwargs):
                return None

            if hasattr(client, "setConnectedCallback"):
                try:
                    client.setConnectedCallback(connected_callback)
                except Exception as exc:
                    variant_result["error"] = str(exc)[:240]
            if hasattr(client, "setMessageReceivedCallback"):
                try:
                    client.setMessageReceivedCallback(message_received_callback)
                except Exception as exc:
                    variant_result["error"] = str(exc)[:240]

            try:
                client.startService()
                variant_result["service_started"] = True
            except Exception as exc:
                variant_result["error"] = str(exc)[:240]
                _ctrader_safe_stop_service(client)
                result["variations"].append(variant_result)
                continue

            connected_event.wait(4)
            if not variant_result["connected"]:
                variant_result["error"] = "connect timeout"

            if variant_result["connected"]:
                auth_result = _ctrader_run_auth_chain(client, runtime)
                variant_result.update(auth_result)
                result["application_auth"] = auth_result.get("application_auth", "failed")
                result["account_list_request"] = auth_result.get("account_list_request", "not_tested")
                result["accounts_found"] = auth_result.get("accounts_found", 0)
                result["accounts"] = auth_result.get("accounts", [])
                result["account_id_match"] = auth_result.get("account_id_match", False)
                result["account_auth"] = auth_result.get("account_auth", "failed")
                result["symbols_request"] = auth_result.get("symbols_request", "failed")
                result["symbols_found"] = auth_result.get("symbols_found", 0)
                result["symbols"] = auth_result.get("symbols", [])
                result["symbols_response_type"] = auth_result.get("symbols_response_type", "")
                result["symbols_response_fields"] = auth_result.get("symbols_response_fields", [])
                result["raw_symbols_count_candidates"] = auth_result.get("raw_symbols_count_candidates", [])
                result["payload_type"] = auth_result.get("payload_type", "")
                result["extracted_message_type"] = auth_result.get("extracted_message_type", "")
                result["extracted_fields"] = auth_result.get("extracted_fields", [])
                result["outer_payload_type"] = auth_result.get("outer_payload_type", "")
                result["decoded_payload_type"] = auth_result.get("decoded_payload_type", "")
                result["decoded_payload_fields"] = auth_result.get("decoded_payload_fields", [])
                result["symbols_field_name"] = auth_result.get("symbols_field_name", "")
                result["first_symbol_type"] = auth_result.get("first_symbol_type", "")
                result["first_symbol_fields"] = auth_result.get("first_symbol_fields", [])
                result["first_symbol_dict"] = auth_result.get("first_symbol_dict", {})
                result["asset_list_request"] = auth_result.get("asset_list_request", "not_tested")
                result["assets_found"] = auth_result.get("assets_found", 0)
                result["assets"] = auth_result.get("assets", [])
                result["asset_response_fields"] = auth_result.get("asset_response_fields", [])
                result["asset_payload_type"] = auth_result.get("asset_payload_type", "")
                result["message"] = auth_result.get("message", "") or "client connected"

            _ctrader_safe_stop_service(client)
            result["variations"].append(variant_result)
            if variant_result["connected"]:
                break

        if not any(v.get("connected") for v in result["variations"]):
            result["message"] = "connect timeout"
            return jsonify(result)

        return jsonify(result)

    except Exception as exc:
        result["protocol_error"] = str(exc)[:240]
        result["message"] = "client diagnostics failed"
        return jsonify(result)


@app.route("/api/trading/live")
def api_trading_live():
    """
    Read-only live market data from cTrader.
    Returns offline+null values gracefully when credentials are missing.
    STRICTLY READ-ONLY – no orders, no position changes, no signals.
    """
    symbol = request.args.get("symbol", "EURUSD").strip().upper()

    # Validate symbol
    if symbol not in TRADING_ASSETS:
        return jsonify({
            "status": "error",
            "message": f"Unbekanntes Symbol: {symbol}. Verfügbar: {', '.join(TRADING_ASSETS.keys())}"
        }), 400

    try:
        runtime = _get_ctrader_runtime()
        mapped = get_mapped_symbol(symbol, runtime=runtime, ensure_cache=True)
        quote = CTRADER_QUOTE_CACHE.get(symbol, {})
        base = _build_trading_response(symbol, "mapped", "symbol mapped, quote subscription pending")
        base["symbol_id"] = mapped.get("symbol_id", "")
        base["description"] = mapped.get("description", "")
        base["display_name"] = mapped.get("display_name", mapped.get("symbolName", symbol))
        base["mapping_source"] = mapped.get("mapping_source", "")
        if quote:
            base.update({
                "status": "online",
                "bid": quote.get("bid"),
                "ask": quote.get("ask"),
                "spread": quote.get("spread"),
                "last_price": quote.get("last_price"),
                "updated_at": quote.get("updated_at"),
                "message": quote.get("message", "live quote"),
            })
        return jsonify(base)

    except Exception as exc:
        return jsonify(_build_trading_response(symbol, "offline", f"cTrader connection error: {str(exc)[:200]}"))


@app.route("/api/trading/quote_test")
def api_trading_quote_test():
    symbol = request.args.get("symbol", "EURUSD").strip().upper()
    runtime = _get_ctrader_runtime()
    normalized_symbol, _ = _normalize_ctrader_symbol(symbol)
    mapped = get_mapped_symbol(normalized_symbol, runtime=runtime, ensure_cache=True)
    response = {
        "symbol": normalized_symbol,
        "symbol_id": mapped.get("symbol_id", ""),
        "symbolName": mapped.get("symbolName", ""),
        "description": mapped.get("description", ""),
        "mapping_source": mapped.get("mapping_source", ""),
        "cache_size": mapped.get("cache_size", 0),
        "known_symbols_sample": mapped.get("known_symbols_sample", []),
        "subscribe_request": "",
        "subscribe_request_sent": False,
        "subscribe_response_received": False,
        "spot_event_received": False,
        "subscribe_symbol_ids": [],
        "subscribe_request_dict": {},
        "subscribe_request_fields": [],
        "subscribe_deferred_result_type": "",
        "subscribe_deferred_result_type_name": "",
        "subscribe_deferred_result_payload_type": "",
        "subscribe_deferred_result_fields": [],
        "subscribe_deferred_callback_called": False,
        "subscribe_deferred_errback_called": False,
        "subscribe_deferred_error": "",
        "subscribe_response_decoded_type": "",
        "subscribe_response_decoded_fields": [],
        "subscribe_response_decoded_dict": {},
        "subscribe_client_msg_id": "",
        "quote_step": "",
        "before_subscribe_reached": False,
        "symbol_id_truthy": bool(mapped.get("symbol_id")),
        "runtime_available": bool(runtime),
        "client_available": False,
        "account_auth_ok": False,
        "callback_registered_before_start": False,
        "callback_registered_before_subscribe": False,
        "callback_invoked_count": 0,
        "connected_callback_count": 0,
        "disconnected_callback_count": 0,
        "subscribe_exception": "",
        "subscribe_exception_type": "",
        "session_error": "",
        "session_error_type": "",
        "received_payload_types": [],
        "received_message_types": [],
        "raw_received_count": 0,
        "timeout_seconds": 5,
        "raw_spot_fields": [],
        "bid": None,
        "ask": None,
        "error": "",
        "wait_started_at": "",
        "wait_finished_at": "",
        "wait_actual_seconds": 0,
        "subscribed_symbol_id": "",
    }
    response["quote_step"] = "quote_test_entered"
    response["quote_step"] = "before_session_start"
    if not response.get("symbol_id"):
        response["mapping_source"] = mapped.get("mapping_source", "")
        response["cache_size"] = mapped.get("cache_size", 0)
        response["known_symbols_sample"] = mapped.get("known_symbols_sample", [])
        response["status"] = "offline"
        response["error"] = "symbol not mapped"
        return jsonify(response)

    runtime_result = {"classes": _ctrader_required_sdk_classes()}
    classes = runtime_result.get("classes") or {}
    available_class_source_id = id(classes)
    classes_for_quote = classes
    classes_for_quote_id = id(classes_for_quote)
    direct_import_ok = False
    direct_import_error = ""
    direct_import_type = ""
    try:
        import importlib
        client_mod = importlib.import_module("ctrader_open_api.client")
        tcp_mod = importlib.import_module("ctrader_open_api.tcpProtocol")
        msg_mod = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        DirectClient = getattr(client_mod, "Client")
        DirectTcpProtocol = getattr(tcp_mod, "TcpProtocol")
        DirectProtoOAApplicationAuthReq = getattr(msg_mod, "ProtoOAApplicationAuthReq")
        DirectProtoOAAccountAuthReq = getattr(msg_mod, "ProtoOAAccountAuthReq")
        DirectProtoOASubscribeSpotsReq = getattr(msg_mod, "ProtoOASubscribeSpotsReq")
        DirectProtoOASubscribeSpotsRes = getattr(msg_mod, "ProtoOASubscribeSpotsRes", None)
        classes_for_quote["Client"] = DirectClient
        classes_for_quote["TcpProtocol"] = DirectTcpProtocol
        classes_for_quote["ProtoOAApplicationAuthReq"] = DirectProtoOAApplicationAuthReq
        classes_for_quote["ProtoOAAccountAuthReq"] = DirectProtoOAAccountAuthReq
        classes_for_quote["ProtoOASubscribeSpotsReq"] = DirectProtoOASubscribeSpotsReq
        if DirectProtoOASubscribeSpotsRes is not None:
            classes_for_quote["ProtoOASubscribeSpotsRes"] = DirectProtoOASubscribeSpotsRes
        direct_import_ok = True
    except Exception as exc:
        direct_import_error = (
            f"{type(exc).__name__}: {str(exc)[:200]} | module=ctrader_open_api.* | traceback={traceback.format_exc(limit=2).strip()[:400]}"
        )
        direct_import_type = type(exc).__name__
    client_cls = classes_for_quote.get("Client")
    tcp_protocol_cls = classes_for_quote.get("TcpProtocol")
    app_auth_cls = classes_for_quote.get("ProtoOAApplicationAuthReq")
    account_auth_cls = classes_for_quote.get("ProtoOAAccountAuthReq")
    subscribe_spots_cls = classes_for_quote.get("ProtoOASubscribeSpotsReq")
    subscribe_spots_res_cls = classes_for_quote.get("ProtoOASubscribeSpotsRes")
    required = [
        "Client",
        "TcpProtocol",
        "ProtoOAApplicationAuthReq",
        "ProtoOAAccountAuthReq",
        "ProtoOASubscribeSpotsReq",
    ]
    class_values_present = {name: classes_for_quote.get(name) is not None for name in required}
    missing = [name for name in required if classes_for_quote.get(name) is None]
    response["class_values_present"] = class_values_present
    response["direct_import_ok"] = direct_import_ok
    response["direct_import_error"] = direct_import_error
    response["direct_import_type"] = direct_import_type
    response["classes_for_quote_keys"] = list(classes_for_quote.keys()) if isinstance(classes_for_quote, dict) else []
    response["classes_for_quote_id"] = classes_for_quote_id
    response["available_class_source_id"] = available_class_source_id
    if missing:
        response["quote_step"] = "session_failed"
        response["session_error"] = "required classes missing"
        response["session_error_type"] = "MissingClasses"
        response["missing_classes"] = missing
        response["available_runtime_keys"] = list(runtime.keys()) if isinstance(runtime, dict) else []
        response["available_class_keys"] = list(classes_for_quote.keys()) if isinstance(classes_for_quote, dict) else []
        response["status"] = "mapped"
        response["error"] = "quote timeout"
        return jsonify(response)

    host, port = _ctrader_endpoint_info()
    reactor_ok, _ = _ctrader_ensure_reactor_running()
    if not reactor_ok:
        response["quote_step"] = "session_failed"
        response["session_error"] = "reactor not running"
        response["session_error_type"] = "RuntimeError"
        response["status"] = "mapped"
        response["error"] = "quote timeout"
        return jsonify(response)

    try:
        client = _ctrader_init_client(client_cls, host, port, tcp_protocol_cls)
    except Exception as e:
        response["quote_step"] = "session_failed"
        response["session_error"] = str(e)[:240]
        response["session_error_type"] = type(e).__name__
        response["status"] = "mapped"
        response["error"] = "quote timeout"
        return jsonify(response)

    response["client_object_present"] = client is not None
    response["client_object_type"] = f"{client.__class__.__module__}.{client.__class__.__name__}" if client is not None else ""
    response["client_available"] = client is not None
    response["quote_step"] = "session_ready"

    connected_event = threading.Event()
    collected = []

    def connected_callback(*args, **kwargs):
        response["connected_callback_count"] += 1
        connected_event.set()

    def disconnected_callback(*args, **kwargs):
        response["disconnected_callback_count"] += 1

    def collect_all(*args):
        response["callback_invoked_count"] += 1
        payload = args[-1] if args else None
        if payload is None:
            return None
        collected.append(payload)
        return None

    if hasattr(client, "setConnectedCallback"):
        try:
            client.setConnectedCallback(connected_callback)
        except Exception:
            pass
    if hasattr(client, "setMessageReceivedCallback"):
        try:
            client.setMessageReceivedCallback(collect_all)
            response["callback_registered_before_start"] = True
        except Exception as exc:
            response["subscribe_exception"] = str(exc)[:240]
            response["subscribe_exception_type"] = type(exc).__name__
    if hasattr(client, "setDisconnectedCallback"):
        try:
            client.setDisconnectedCallback(disconnected_callback)
        except Exception:
            pass

    response["callback_registered_before_subscribe"] = False

    try:
        client.startService()
    except Exception as e:
        response["quote_step"] = "session_failed"
        response["session_error"] = str(e)[:240]
        response["session_error_type"] = type(e).__name__
        response["status"] = "mapped"
        response["error"] = "quote timeout"
        _ctrader_safe_stop_service(client)
        return jsonify(response)

    if not connected_event.wait(4):
        response["quote_step"] = "session_failed"
        response["session_error"] = "connect timeout"
        response["session_error_type"] = "TimeoutError"
        response["status"] = "mapped"
        response["error"] = "quote timeout"
        _ctrader_safe_stop_service(client)
        return jsonify(response)

    time.sleep(2)

    try:
        app_req = app_auth_cls()
        if hasattr(app_req, "clientId"):
            app_req.clientId = runtime["client_id"]
        if hasattr(app_req, "clientSecret"):
            app_req.clientSecret = runtime["client_secret"]
        _ctrader_send_request_and_wait(client, app_req, "application", timeout=6)

        account_req = account_auth_cls()
        if hasattr(account_req, "ctidTraderAccountId"):
            account_req.ctidTraderAccountId = int(runtime["account_id"])
        if hasattr(account_req, "accessToken"):
            account_req.accessToken = runtime["access_token"]
        _ctrader_send_request_and_wait(client, account_req, "account", timeout=6)
    except Exception as e:
        response["quote_step"] = "session_failed"
        response["session_error"] = str(e)[:240]
        response["session_error_type"] = type(e).__name__
        response["status"] = "mapped"
        response["error"] = "quote timeout"
        _ctrader_safe_stop_service(client)
        return jsonify(response)

    response["client_available"] = True
    response["account_auth_ok"] = True
    response["before_subscribe_reached"] = True
    response["quote_step"] = "before_subscribe"
    response["subscribe_request"] = "ProtoOASubscribeSpotsReq"
    response["subscribe_symbol_ids"] = [int(response["symbol_id"])]
    response["callback_registered_before_subscribe"] = True

    try:
        subscribe_req = subscribe_spots_cls()
        if hasattr(subscribe_req, "ctidTraderAccountId"):
            subscribe_req.ctidTraderAccountId = int(runtime["account_id"])
        if hasattr(subscribe_req, "symbolId"):
            subscribe_req.symbolId.append(int(response["symbol_id"]))
        response["subscribe_client_msg_id"] = f"quote_subscribe_{normalized_symbol}_{int(time.time() * 1000)}"
        if hasattr(subscribe_req, "clientMsgId"):
            subscribe_req.clientMsgId = response["subscribe_client_msg_id"]
        if hasattr(subscribe_req, "subscribeToSpotTimestamp"):
            try:
                subscribe_req.subscribeToSpotTimestamp = int(time.time() * 1000)
            except Exception:
                pass
        try:
            from google.protobuf.json_format import MessageToDict  # type: ignore
            response["subscribe_request_dict"] = MessageToDict(subscribe_req, preserving_proto_field_name=True)
        except Exception:
            response["subscribe_request_dict"] = {}
        try:
            response["subscribe_request_fields"] = [
                {
                    "name": getattr(field[0], "name", ""),
                    "value": list(field[1]) if hasattr(field[1], "__iter__") and not isinstance(field[1], (str, bytes, dict)) else str(field[1]),
                }
                for field in subscribe_req.ListFields()
            ]
        except Exception:
            response["subscribe_request_fields"] = []
        try:
            response["subscribe_symbol_ids"] = [int(x) for x in getattr(subscribe_req, "symbolId", [])]
        except Exception:
            response["subscribe_symbol_ids"] = []
        d = client.send(subscribe_req)
        response["subscribe_request_sent"] = True
        response["subscribe_response_received"] = "not_waited"
        response["subscribe_deferred_result_type"] = type(d).__name__ if d is not None else ""
        response["subscribe_deferred_callback_called"] = False
        response["subscribe_deferred_errback_called"] = False
        response["subscribe_deferred_result_type_name"] = ""
        response["subscribe_deferred_result_payload_type"] = ""
        response["subscribe_deferred_result_fields"] = []
        response["subscribe_deferred_error"] = ""
        def on_subscribe_cb(result):
            response["subscribe_deferred_callback_called"] = True
            response["subscribe_deferred_result_type_name"] = f"{result.__class__.__module__}.{result.__class__.__name__}"
            response["subscribe_deferred_result_payload_type"] = str(getattr(result, "payloadType", ""))
            try:
                response["subscribe_deferred_result_fields"] = [field.name for field, value in result.ListFields()]
            except Exception:
                response["subscribe_deferred_result_fields"] = []
            payload_bytes = getattr(result, "payload", None)
            if isinstance(payload_bytes, (bytes, bytearray)):
                decoded = None
                if subscribe_spots_res_cls is not None:
                    try:
                        decoded = subscribe_spots_res_cls()
                        decoded.ParseFromString(payload_bytes)
                    except Exception as exc:
                        response["subscribe_response_decoded_type"] = f"decode_error:{type(exc).__name__}"
                        decoded = None
                if decoded is not None:
                    response["subscribe_response_decoded_type"] = f"{decoded.__class__.__module__}.{decoded.__class__.__name__}"
                    try:
                        response["subscribe_response_decoded_fields"] = [field.name for field, value in decoded.ListFields()]
                    except Exception:
                        response["subscribe_response_decoded_fields"] = []
                    try:
                        from google.protobuf.json_format import MessageToDict  # type: ignore
                        response["subscribe_response_decoded_dict"] = MessageToDict(decoded, preserving_proto_field_name=True)
                    except Exception:
                        response["subscribe_response_decoded_dict"] = {}
                    response["subscribe_response_received"] = True
            return result

        def on_subscribe_eb(failure):
            response["subscribe_deferred_errback_called"] = True
            response["subscribe_deferred_error"] = str(failure)
            return failure

        if hasattr(d, "addCallbacks"):
            d.addCallbacks(on_subscribe_cb, on_subscribe_eb)
        response["quote_step"] = "subscribe_sent"
    except Exception as e:
        response["subscribe_exception"] = str(e)[:240]
        response["subscribe_exception_type"] = type(e).__name__
        response["status"] = "mapped"
        response["error"] = "no spot event received"
        _ctrader_safe_stop_service(client)
        return jsonify(response)

    response["wait_started_at"] = datetime.utcnow().isoformat() + "Z"
    deadline = time.time() + 5
    while time.time() < deadline:
        time.sleep(0.05)
    response["wait_finished_at"] = datetime.utcnow().isoformat() + "Z"
    response["wait_actual_seconds"] = 5

    response["raw_received_count"] = len(collected)
    response["received_payload_types"] = [str(getattr(item, "payloadType", "") or getattr(item, "payload_type", "") or "") for item in collected if getattr(item, "payloadType", "") or getattr(item, "payload_type", "")]
    response["received_message_types"] = [str(_ctrader_message_name(item)) for item in collected if _ctrader_message_name(item)]
    try:
        response["subscribed_symbol_id"] = int(response["subscribe_symbol_ids"][0]) if response.get("subscribe_symbol_ids") else ""
    except Exception:
        response["subscribed_symbol_id"] = ""

    spot_payload = None
    for item in collected:
        message_type = _ctrader_message_name(item).lower()
        payload_type = str(getattr(item, "payloadType", "") or getattr(item, "payload_type", "") or "").lower()
        if "spot" in message_type or "spot" in payload_type:
            spot_payload = item
            break

    if spot_payload is not None:
        quote = _ctrader_extract_spot_quote(spot_payload)
        response["spot_event_received"] = True
        response["bid"] = quote.get("bid")
        response["ask"] = quote.get("ask")
        response["error"] = "live quote"
        response["status"] = "online"
    else:
        response["status"] = "mapped"
        response["error"] = "subscribe ok, no spot event received"

    _ctrader_safe_stop_service(client)
    return jsonify(response)


@app.route("/api/trading/quotes")
def api_trading_quotes():
    return jsonify({
        "status": "ok",
        "quotes": CTRADER_QUOTE_CACHE,
        "count": len(CTRADER_QUOTE_CACHE),
        "stream": dict(CTRADER_STREAM_STATUS),
    })


@app.route("/api/trading/start_stream")
def api_trading_start_stream():
    thread, started = _ctrader_start_stream_thread()
    with CTRADER_STREAM_LOCK:
        status = dict(CTRADER_STREAM_STATUS)
    if started:
        status["message"] = "background stream started"
    else:
        status["message"] = "background stream already running"
    status["thread_alive"] = bool(thread and thread.is_alive())
    return jsonify({
        "status": "prepared",
        "message": "background stream endpoint prepared",
        "stream": status,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
