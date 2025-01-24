def generate_commentary(event):
    """
    Generate commentary based on match event.
    """
    event_type = event["type"]
    minute = event["time"]["elapsed"]
    player = event.get("player", {}).get("name", "Unknown Player")

    if event_type == "Goal":
        return f"GOAL! {player} scores a brilliant goal at {minute}'!"
    elif event_type == "Card":
        card = event.get("detail", "card")
        return f"A {card} card is shown to {player} at {minute}'!"
    elif event_type == "Substitution":
        player_out = event.get("assist", {}).get("name", "Unknown Player")
        return f"{player_out} is substituted by {player} at {minute}'!"
    else:
        return f"An event occurred at {minute}'!"