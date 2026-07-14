from __future__ import annotations

import copy
import ipaddress
import re
from datetime import date
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .actionable import SOURCE_KINDS


class SourceValidationError(ValueError):
    pass


SOURCE_PRIORITY = {
    "video_source": 0,
    "official_source": 1,
    "third_party_source": 2,
    "ai_teaching": 3,
    "transfer_exercise": 4,
    "needs_confirmation": 5,
}

_NETWORK_KINDS = {"official_source", "third_party_source"}
_MERGE_FIELDS = (
    "title",
    "publisher",
    "version",
    "checked_at",
    "version_warning",
)
_TRACKING_PARAMETERS = {"spm_id_from", "vd_source", "from", "source"}
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_DNS_LABEL_PATTERN = re.compile(r"[A-Za-z0-9-]+\Z")


def canonicalize_url(url: str) -> str:
    try:
        if not isinstance(url, str):
            raise SourceValidationError("url must be a string")
        if any(ord(char) < 32 or ord(char) == 127 for char in url):
            raise SourceValidationError("url contains control characters")
        value = url.strip()
        if not value or any(char.isspace() for char in value):
            raise SourceValidationError("url contains whitespace or control characters")

        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            raise SourceValidationError("url scheme must be http or https")
        if parsed.username is not None or parsed.password is not None:
            raise SourceValidationError("url credentials are not allowed")
        host = parsed.hostname
        if not host:
            raise SourceValidationError("url must include a host")
        host, is_ipv6 = _canonicalize_host(host)
        port = parsed.port
        if is_ipv6:
            host = f"[{host}]"
        if port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
            host = f"{host}:{port}"

        query_items = []
        for key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
            lowered = key.casefold()
            if lowered.startswith("utm_") or lowered in _TRACKING_PARAMETERS:
                continue
            query_items.append((key, query_value))
        query_items.sort()
        return urlunsplit((scheme, host, parsed.path or "/", urlencode(query_items), ""))
    except SourceValidationError:
        raise
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SourceValidationError("invalid url") from exc


def validate_source(source: dict[str, Any]) -> None:
    try:
        if not isinstance(source, dict):
            raise SourceValidationError("source must be an object")
        source_id = source.get("id")
        if not _is_safe_text(source_id):
            raise SourceValidationError("source id must be a nonempty safe string")
        kind = source.get("kind")
        if not isinstance(kind, str) or kind not in SOURCE_KINDS:
            raise SourceValidationError("source kind is invalid")
        if kind not in SOURCE_PRIORITY:
            raise SourceValidationError("source kind has no priority")
        if not _is_nonempty_text(source.get("title")):
            raise SourceValidationError("source title must be a nonempty string")

        if kind in _NETWORK_KINDS:
            canonicalize_url(source.get("url"))
            _validate_date(source.get("checked_at"))
        elif "url" in source and source["url"] is not None:
            canonicalize_url(source["url"])
        if kind == "video_source" and "checked_at" in source and source["checked_at"] is not None:
            _validate_date(source["checked_at"])
        if kind == "third_party_source" and not _is_nonempty_text(source.get("version_warning")):
            raise SourceValidationError("third_party_source requires version_warning")
        if "claims" in source:
            claims = source["claims"]
            if not isinstance(claims, list) or any(not _is_nonempty_text(item) for item in claims):
                raise SourceValidationError("claims must be a list of nonempty strings")
    except SourceValidationError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise SourceValidationError("invalid source") from exc


def normalize_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        if not isinstance(sources, list):
            raise SourceValidationError("sources must be a list")

        prepared = []
        ids: set[str] = set()
        for index, source in enumerate(sources):
            validate_source(source)
            source_id = source["id"]
            if source_id in ids:
                raise SourceValidationError(f"duplicate source id: {source_id}")
            ids.add(source_id)
            item = copy.deepcopy(source)
            if "url" in item and item["url"] is not None:
                item["url"] = canonicalize_url(item["url"])
            prepared.append((index, item))

        groups: list[dict[str, Any]] = []
        network_groups: dict[str, dict[str, Any]] = {}
        for index, item in prepared:
            key = item.get("url") if item["kind"] in _NETWORK_KINDS else None
            group = network_groups.get(key) if key is not None else None
            if group is None:
                group = {"first": index, "items": []}
                groups.append(group)
                if key is not None:
                    network_groups[key] = group
            group["items"].append((index, item))

        normalized = []
        for group in groups:
            entries = group["items"]
            winner_index, winner = min(
                entries, key=lambda entry: (SOURCE_PRIORITY[entry[1]["kind"]], entry[0])
            )
            result = copy.deepcopy(winner)
            for field in _MERGE_FIELDS:
                if not _is_nonempty_value(result.get(field)):
                    for _, candidate in entries:
                        if _is_nonempty_value(candidate.get(field)):
                            result[field] = copy.deepcopy(candidate[field])
                            break
            claims = []
            for _, candidate in entries:
                for claim in candidate.get("claims", []):
                    if claim not in claims:
                        claims.append(claim)
            if claims:
                result["claims"] = claims
            normalized.append((SOURCE_PRIORITY[result["kind"]], group["first"], result))

        normalized.sort(key=lambda entry: (entry[0], entry[1]))
        return [item for _, _, item in normalized]
    except SourceValidationError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise SourceValidationError("invalid sources") from exc


def _is_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_safe_text(value: Any) -> bool:
    return (
        _is_nonempty_text(value)
        and value == value.strip()
        and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
    )


def _is_nonempty_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None and value != []


def _canonicalize_host(host: str) -> tuple[str, bool]:
    if (
        "%" in host
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in host)
        or host.startswith(".")
        or host.endswith(".")
        or ".." in host
    ):
        raise SourceValidationError("invalid url host")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if ":" in host or re.fullmatch(r"[0-9.]+", host):
            raise SourceValidationError("invalid IP address")
    else:
        return address.compressed.lower(), address.version == 6

    encoded_labels = []
    for label in host.split("."):
        try:
            encoded = label.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise SourceValidationError("invalid DNS host") from exc
        if (
            not encoded
            or len(encoded) > 63
            or not _DNS_LABEL_PATTERN.fullmatch(encoded)
            or encoded.startswith("-")
            or encoded.endswith("-")
        ):
            raise SourceValidationError("invalid DNS host")
        encoded_labels.append(encoded.lower())
    result = ".".join(encoded_labels)
    if len(result) > 253:
        raise SourceValidationError("DNS host is too long")
    return result, False


def _validate_date(value: Any) -> None:
    if not isinstance(value, str) or not _DATE_PATTERN.fullmatch(value):
        raise SourceValidationError("checked_at must use YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SourceValidationError("checked_at must be a real date") from exc
