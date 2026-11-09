"""
title: d3 Native Vision Candlestick Strategy Router
author: Quantitative AI Architect
version: 4.1.0
required_open_webui_version: 0.4.0
"""

import json
import re
import urllib.request
import urllib.error
from typing import Union, Optional

OLLAMA_URL = "http://192.168.10.153:11434"


class Pipe:
    def __init__(self):
        pass

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

                # 5. Iteratively parse calibrated confidence probabilities
                for q_name, q_data in answers.items():
                    probs = q_data.get("probabilities", {}) or q_data.get(
                        "predictions", {}
                    )
                    if probs:
                        top_choice = max(probs, key=probs.get)
                        extracted_decisions[q_name] = top_choice

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
                    output_lines.append(
                        "🟢 **STRATEGY: STRONG BUY (A+ Setup)**\nConfluence confirmed. Trend vector, continuation pattern, and structural support convergence met."
                    )
                elif (
                    m_struct == "downtrend"
                    and s_pattern in ["pin_bear", "engulf_bear"]
                    and k_level == "yes"
                ):
                    output_lines.append(
                        "🔴 **STRATEGY: STRONG SHORT (A+ Setup)**\nConfluence confirmed. Trend vector, rejection pattern, and structural resistance convergence met."
                    )
                elif m_struct == "uptrend" and s_pattern in ["pin_bull", "engulf_bull"]:
                    output_lines.append(
                        "yellow_circle **STRATEGY: SCALED LONG (B Setup)**\nTrend and pattern match, but structural key level confirmation is floating or unverified."
                    )
                else:
                    output_lines.append(
                        "⚪ **STRATEGY: NO TRADE (Cash Position)**\nMarket matrices do not meet minimum convergence thresholds for automated execution rules."
                    )

                return "\n".join(output_lines)

        except urllib.error.HTTPError as e:
            return f"Ollama API Rejected Payload (HTTP {e.code}):\n```json\n{e.read().decode('utf-8')}\n```"
        except Exception as e:
            return f"Runtime error tracking decision execution: {str(e)}"
