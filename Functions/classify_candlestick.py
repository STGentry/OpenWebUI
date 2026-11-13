"""
title: d3 Native Vision Candlestick Strategy Router
author: Quantitative AI Architect
version: 4.2.0
required_open_webui_version: 0.4.0
"""

import json
import re
import urllib.request
import urllib.error
from typing import Union, Optional

OLLAMA_URL = "<<insert ip here>>"


class Pipe:
    def __init__(self):
        pass

    def _sizing(self, base_size: float, confidence: float):
        """Map a tier's base size and the composite confidence score to a final position size."""
        if confidence >= 70:
            multiplier = 1.0
        elif confidence >= 50:
            multiplier = 0.5
        else:
            multiplier = 0.0
        return base_size * multiplier, multiplier

    def _render_trade_plan(
        self, title: str, rationale: str, spec: dict, confidence: float
    ) -> list:
        """Render an actionable trade-plan table for a routed strategy tier."""
        base_size = spec.get("base_size", 1.0)
        final_size, multiplier = self._sizing(base_size, confidence)

        if multiplier == 0.0:
            size_rule = (
                "0% of standard risk unit — below 50% confidence floor; observe only, no execution "
                f"(composite confidence {confidence:.1f}%)"
            )
        else:
            size_rule = (
                f"{final_size * 100:.0f}% of standard risk unit "
                f"({base_size * 100:.0f}% base x {multiplier:g} confidence multiplier @ {confidence:.1f}% confidence)"
            )

        rows = [
            ("Entry Trigger", spec["entry"]),
            ("Stop-Loss", spec["stop"]),
            ("Take-Profit", spec["target"]),
            ("Risk:Reward", spec["rr"]),
            ("Position Size", size_rule),
            ("Invalidation", spec["invalidation"]),
            ("Time Validity", spec["validity"]),
        ]

        lines = [
            f"**{title}** — {rationale}",
            "",
            "| Parameter | Rule |",
            "| --- | --- |",
        ]
        for label, rule in rows:
            lines.append(f"| **{label}** | {rule} |")
        lines.append("")
        return lines

    def _render_checklist(
        self, m_struct: str, s_pattern: str, k_level: str, confidence: float
    ) -> list:
        """Render the pre-trade checklist auto-checked from the decision vectors."""
        directional = (
            (m_struct == "uptrend" and s_pattern in ["pin_bull", "engulf_bull"])
            or (m_struct == "downtrend" and s_pattern in ["pin_bear", "engulf_bear"])
        )

        items = [
            (
                m_struct in ("uptrend", "downtrend"),
                f"Trend alignment (market_structure = {m_struct})",
            ),
            (
                s_pattern != "neutral_or_none",
                f"Pattern quality (signal_pattern = {s_pattern})",
            ),
            (k_level == "yes", f"Key-level confluence (key_level = {k_level})"),
            (directional, "Directional consistency (trend and pattern agree)"),
            (
                confidence >= 50,
                f"Confidence floor (composite = {confidence:.1f}%, floor = 50%)",
            ),
        ]

        lines = ["### ✅ Pre-Trade Checklist"]
        for passed, label in items:
            lines.append(f"- [{'x' if passed else ' '}] {label}")
        lines.append("")
        return lines

    def pipe(self, body: dict) -> str:
        """Classify the uploaded candlestick image natively using the d3 vision decision model.

        Args:
            body: Open WebUI message payload dictionary.
        """
        messages = body.get("messages", [])
        if not messages:
            return json.dumps({"error": "No messages found in the Open WebUI payload."})

        last_message = messages[-1]
        raw_content = last_message.get("content", "")

        content = ""
        image_b64 = None

        # 1. Safely extract standard base64 strings and filter text data layers
        if isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, str):
                    content += " " + item
                elif isinstance(item, dict):
                    if item.get("type") == "text":
                        content += " " + item.get("text", "")
                    elif item.get("type") == "image_url" and isinstance(
                        item.get("image_url"), dict
                    ):
                        url_val = item["image_url"].get("url", "")
                        if "base64," in url_val:
                            image_b64 = url_val.split("base64,", 1)[1].strip()
                        else:
                            image_b64 = url_val
        else:
            content = str(raw_content)

        # 2. Extract embedded text/markdown image structures
        if not image_b64:
            md_match = re.search(
                r"!\[.*?\]\(data:image/[^;]+;base64,([^)]+)\)", content
            )
            if md_match:
                image_b64 = md_match.group(1).strip()
            else:
                html_match = re.search(
                    r'<img\s+[^>]*src=["\']data:image/[^;]+;base64,([^"\']+)["\'][^>]*>',
                    content,
                )
                if html_match:
                    image_b64 = html_match.group(1).strip()

        if not image_b64 and "base64," in content:
            try:
                parts = content.split("base64,")
                if len(parts) > 1:
                    image_b64 = parts[1].split()[0].strip(")\"'<>")
            except Exception:
                pass

        if not image_b64:
            return "Error: No chart image found. Please upload or paste a candlestick chart directly into the chat window."

        # 3. Formulate the strict /v1/systemone specification mapping key criteria explicitly
        payload_dict = {
            "model": "d3:27b",
            "state": "Analyze the technical structure of this candlestick chart.",
            "images": [image_b64],
            "questions": {
                "market_structure": {
                    "type": "choice",
                    "instructions": "Is the visible price sequence showing clear higher-highs/higher-lows or lower-highs/lower-lows?",
                    "criteria": {
                        "uptrend": "Showing higher highs and higher lows across recent periods.",
                        "downtrend": "Showing lower highs and lower lows across recent periods.",
                        "neutral": "No clear directional layout, range-bound, or consolidating.",
                    },
                },
                "signal_pattern": {
                    "type": "choice",
                    "instructions": "Which candlestick pattern matches the most recent signal candle?",
                    "criteria": {
                        "pin_bull": "Long lower wick, small body, close near high.",
                        "pin_bear": "Long upper wick, small body, close near low.",
                        "engulf_bull": "Green body fully covers prior red candle body.",
                        "engulf_bear": "Red body fully covers prior green candle body.",
                        "neutral_or_none": "No distinct candlestick structures matching execution metrics.",
                    },
                },
                "key_level": {
                    "type": "choice",
                    "instructions": "Is the signal candle interacting with a major horizontal support, resistance, or moving average?",
                    "criteria": {
                        "yes": "Candle is resting directly on or strongly rejecting a structural key level.",
                        "no": "Candle is floating in open space between clear key chart levels.",
                    },
                },
            },
        }

        payload = json.dumps(payload_dict).encode("utf-8")

        # 4. Route calculations through the System One API endpoint contract
        req = urllib.request.Request(
            f"{OLLAMA_URL}/v1/systemone",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw_response = resp.read().decode("utf-8")
                data = json.loads(raw_response)

                answers = data.get("answers", {})

                output_lines = [
                    "### 📊 d3:27b Candlestick Analysis Matrix (Native SystemOne Vision)\n",
                    "The model has evaluated your image and computed the following mathematical probabilities:\n",
                ]

                extracted_decisions = {}
                top_probs = {}

                # 5. Iteratively parse calibrated confidence probabilities
                for q_name, q_data in answers.items():
                    probs = q_data.get("probabilities", {}) or q_data.get(
                        "predictions", {}
                    )
                    if probs:
                        top_choice = max(probs, key=probs.get)
                        extracted_decisions[q_name] = top_choice
                        top_probs[q_name] = float(probs[top_choice])

                        output_lines.append(
                            f"#### 🔍 {q_name.replace('_', ' ').title()}"
                        )
                        for choice, val in probs.items():
                            marker = "🎯 **" if choice == top_choice else "- "
                            end_marker = "**" if choice == top_choice else ""
                            output_lines.append(
                                f"{marker}`{choice}`: {float(val)*100:.2f}%{end_marker}"
                            )
                        output_lines.append("")

                # 5.5 Composite confidence score across all decision vectors
                if top_probs:
                    confidence = (sum(top_probs.values()) / len(top_probs)) * 100
                else:
                    confidence = 0.0

                output_lines.append(
                    f"### 📈 Composite Confidence: **{confidence:.1f}%** "
                    f"(mean of {len(top_probs)} top-choice probabilities)\n"
                )

                # 6. Execute deterministic strategy routing via matching state vectors
                m_struct = extracted_decisions.get("market_structure", "neutral")
                s_pattern = extracted_decisions.get("signal_pattern", "neutral_or_none")
                k_level = extracted_decisions.get("key_level", "no")

                output_lines.append(
                    "---\n### 🎯 Derived Quantitative Strategy Recommendation"
                )

                if (
                    m_struct == "uptrend"
                    and s_pattern in ["pin_bull", "engulf_bull"]
                    and k_level == "yes"
                ):
                    output_lines.extend(
                        self._render_trade_plan(
                            "🟢 STRATEGY: STRONG BUY (A+ Setup)",
                            "Confluence confirmed: trend vector, continuation pattern, and structural support convergence met.",
                            {
                                "base_size": 1.0,
                                "entry": "Buy-stop order 1 tick above the signal-candle high (or market at signal-candle close).",
                                "stop": "Below the signal-candle low (wick extreme) plus a small buffer (0.1x range or 1 ATR).",
                                "target": "TP1: key-level retest (~1R). TP2: opposite visible-range extreme / measured move (~2R).",
                                "rr": "Target ~2R; do not execute if expected reward < 1.5R.",
                                "invalidation": "Any close beyond the stop level, or rejection back inside the key level.",
                                "validity": "Valid for the next 3 candles only; if not triggered, cancel.",
                            },
                            confidence,
                        )
                    )
                elif (
                    m_struct == "downtrend"
                    and s_pattern in ["pin_bear", "engulf_bear"]
                    and k_level == "yes"
                ):
                    output_lines.extend(
                        self._render_trade_plan(
                            "🔴 STRATEGY: STRONG SHORT (A+ Setup)",
                            "Confluence confirmed: trend vector, rejection pattern, and structural resistance convergence met.",
                            {
                                "base_size": 1.0,
                                "entry": "Sell-stop order 1 tick below the signal-candle low (or market at signal-candle close).",
                                "stop": "Above the signal-candle high (wick extreme) plus a small buffer (0.1x range or 1 ATR).",
                                "target": "TP1: key-level retest (~1R). TP2: opposite visible-range extreme / measured move (~2R).",
                                "rr": "Target ~2R; do not execute if expected reward < 1.5R.",
                                "invalidation": "Any close beyond the stop level, or rejection back inside the key level.",
                                "validity": "Valid for the next 3 candles only; if not triggered, cancel.",
                            },
                            confidence,
                        )
                    )
                elif m_struct == "uptrend" and s_pattern in ["pin_bull", "engulf_bull"]:
                    output_lines.extend(
                        self._render_trade_plan(
                            "🟡 STRATEGY: SCALED LONG (B Setup)",
                            "Trend and pattern match, but structural key level confirmation is floating or unverified — execute reduced size.",
                            {
                                "base_size": 0.5,
                                "entry": "Tranche 1: buy-stop 1 tick above the signal-candle high (50% of size). Tranche 2: add the remaining 50% on the next confirming close above the prior candle's high.",
                                "stop": "Below the signal-candle low (wick extreme).",
                                "target": "Halved: take profit at ~1R (nearest visible swing extreme).",
                                "rr": "Target ~1R; execute at half size to compensate for the missing structural confluence.",
                                "invalidation": "Any close beyond the stop level, or a bearish close back inside the prior range.",
                                "validity": "Valid for the next 3 candles only; if not triggered, cancel.",
                            },
                            confidence,
                        )
                    )
                elif m_struct == "downtrend" and s_pattern in ["pin_bear", "engulf_bear"]:
                    output_lines.extend(
                        self._render_trade_plan(
                            "🟡 STRATEGY: SCALED SHORT (B Setup)",
                            "Trend and pattern match, but structural key level confirmation is floating or unverified — execute reduced size.",
                            {
                                "base_size": 0.5,
                                "entry": "Tranche 1: sell-stop 1 tick below the signal-candle low (50% of size). Tranche 2: add the remaining 50% on the next confirming close below the prior candle's low.",
                                "stop": "Above the signal-candle high (wick extreme).",
                                "target": "Halved: take profit at ~1R (nearest visible swing extreme).",
                                "rr": "Target ~1R; execute at half size to compensate for the missing structural confluence.",
                                "invalidation": "Any close beyond the stop level, or a bullish close back inside the prior range.",
                                "validity": "Valid for the next 3 candles only; if not triggered, cancel.",
                            },
                            confidence,
                        )
                    )
                else:
                    output_lines.append(
                        "⚪ **STRATEGY: NO TRADE (Cash Position)** — market matrices do not meet minimum convergence thresholds for automated execution rules."
                    )
                    output_lines.append("")

                    failed = []
                    if m_struct not in ("uptrend", "downtrend"):
                        failed.append(f"trend alignment (market_structure = {m_struct})")
                    if s_pattern == "neutral_or_none":
                        failed.append(f"pattern quality (signal_pattern = {s_pattern})")
                    if k_level != "yes":
                        failed.append(f"key-level confluence (key_level = {k_level})")
                    directional = (
                        (
                            m_struct == "uptrend"
                            and s_pattern in ["pin_bull", "engulf_bull"]
                        )
                        or (
                            m_struct == "downtrend"
                            and s_pattern in ["pin_bear", "engulf_bear"]
                        )
                    )
                    if not directional:
                        failed.append(
                            "directional consistency (trend and pattern do not agree)"
                        )
                    if confidence < 50:
                        failed.append(
                            f"confidence floor (composite = {confidence:.1f}% < 50% execution floor)"
                        )

                    output_lines.append("**Failed conditions:**")
                    for cond in failed:
                        output_lines.append(f"- ✗ {cond}")
                    output_lines.append("")

                    if m_struct == "uptrend":
                        output_lines.append(
                            "**Trigger for a long:** bullish pin bar or engulfing at key support during a confirmed uptrend."
                        )
                    elif m_struct == "downtrend":
                        output_lines.append(
                            "**Trigger for a short:** bearish pin bar or engulfing at key resistance during a confirmed downtrend."
                        )
                    else:
                        output_lines.append(
                            "**Trigger:** establish a directional trend (higher highs/lows or lower highs/lows), then a confluence signal candle at a key level."
                        )
                    output_lines.append("")

                output_lines.extend(
                    self._render_checklist(m_struct, s_pattern, k_level, confidence)
                )

                return "\n".join(output_lines)

        except urllib.error.HTTPError as e:
            return f"Ollama API Rejected Payload (HTTP {e.code}):\n```json\n{e.read().decode('utf-8')}\n```"
        except Exception as e:
            return f"Runtime error tracking decision execution: {str(e)}"
