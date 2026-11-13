import random
import re


class Tools:
    def __init__(self):
        pass

    def roll_dice(self, prompt: str) -> str:
        """
        Use this tool whenever a dice roll is required for NPCs, monsters, or environmental checks.
        Accepts standard dice notation like '1d20', '2d6+4', or '1d100'.
        :param prompt: The dice notation string (e.g., '1d20+5').
        """
        # Remove any spaces and convert to lowercase
        clean_prompt = prompt.lower().strip().replace(" ", "")

        # Regex: (number of dice)d(number of sides)(+/-)(modifier)
        match = re.match(r"(\d+)d(\d+)([+-]\d+)?", clean_prompt)

        if not match:
            return "Error: Invalid notation. Please use '1d20' or '2d6+4'."

        # Extract values
        count = int(match.group(1))
        sides = int(match.group(2))
        modifier_str = match.group(3)
        modifier = int(modifier_str) if modifier_str else 0

        # Perform the rolls
        rolls = [random.randint(1, sides) for _ in range(count)]
        total_rolls = sum(rolls)
        final_result = total_rolls + modifier

        # Format the output for the DM
        return f"Rolls: {rolls} | Sum: {total_rolls} | Modifier: {modifier_str if modifier_str else '0'} | Total: {final_result}"
