"""Laws of the Game digest used to ground Call Review analysis.

The agent is told to read the relevant laws BEFORE judging the video, and to
cite specific Law numbers in its reasoning. This is a concise, faithful digest
of the IFAB Laws of the Game (2025/26) plus competition-specific notes.
"""

# A concise per-law digest. Each entry: number + title + key points.
LAWS_DIGEST = [
    {
        "law": "Law 5",
        "title": "The Referee",
        "points": [
            "The referee is the sole judge of fact and enforces the Laws.",
            "Decisions are final unless VAR identifies a clear and obvious error.",
        ],
    },
    {
        "law": "Law 11",
        "title": "Offside",
        "points": [
            "A player is offside if any part of the head, body or feet is nearer to the opponents' goal line than both the ball and the second-last opponent.",
            "Hands and arms are not judged for offside.",
            "Offence only if involved in active play: interfering with play, interfering with an opponent, or gaining an advantage.",
            "Not an offence when receiving the ball directly from a goal kick, throw-in or corner kick.",
        ],
    },
    {
        "law": "Law 12",
        "title": "Fouls and Misconduct",
        "points": [
            "Direct free kick (or penalty if inside the area): charging, jumping at, kicking, pushing, striking, tackling, tripping an opponent; holding; handling the ball; biting or spitting.",
            "Careless = no caution; reckless = yellow card; excessive force = red card (serious foul play).",
            "DOGSO (denying an obvious goal-scoring opportunity): outside the area = red card; inside the area = red only for deliberate handball or foul that is not a genuine attempt to play the ball, otherwise yellow.",
            "Handball: deliberate handball is an offence; also when the hand/arm makes the body unnaturally bigger or is above shoulder height; no offence if the ball comes off the player's own body first or from close range with no time to react.",
            "Yellow card: unsporting behaviour, dissent, persistent infringement, delaying restart. Red card: serious foul play, violent conduct, spitting, deliberate handball denying a goal, offensive language.",
        ],
    },
    {
        "law": "Law 14",
        "title": "The Penalty Kick",
        "points": [
            "A penalty is awarded for a direct free kick offence committed inside the penalty area.",
            "Ball on the spot; goalkeeper on the line; all other players outside the area and behind the ball.",
            "If the goalkeeper infringes and the kick is missed/saved, the kick is retaken; if the kicker's teammates encroach, the kick is retaken only if the ball enters the goal.",
        ],
    },
    {
        "law": "Laws 7-10",
        "title": "Match basics",
        "points": [
            "Goal scored when the whole of the ball passes over the goal line, between the posts and under the crossbar, provided no offence has been committed.",
            "Ball in/out of play: out when it wholly crosses the boundary lines.",
        ],
    },
    {
        "law": "VAR Protocol",
        "title": "Video Assistant Referee",
        "points": [
            "VAR reviews only clear and obvious errors or missed serious incidents in four match-changing situations: goal/no goal, penalty/no penalty, direct red cards, and mistaken identity.",
            "Factual decisions (offside position, ball out of play, encroachment) can be corrected objectively; subjective decisions are reviewed only for clear and obvious error.",
            "The referee always makes the final decision after viewing the monitor or acting on the VAR's recommendation.",
        ],
    },
]

# Competition-specific notes. "Other" falls back to pure IFAB.
COMPETITION_NOTES = {
    "La Liga": [
        "La Liga applies the IFAB Laws of the Game as adopted by RFEF.",
        "RFEF/Laliga directives emphasize that only the team captain may approach the referee to discuss a decision.",
        "VAR is used in all La Liga matches under the standard IFAB protocol.",
    ],
    "UEFA Champions League": [
        "UEFA competitions apply the IFAB Laws of the Game plus UEFA's competition regulations.",
        "UEFA instructs referees to protect player safety and use the captain-only rule when managing player conduct.",
        "UEFA enforces strict sanctions for simulation and for players surrounding the referee.",
        "VAR follows the standard IFAB protocol with UEFA's clear-and-obvious-error guidance.",
    ],
}


def get_laws_context(competition: str = "La Liga", decision_type: str | None = None) -> str:
    """Build the laws text the agent must read before judging the clip."""
    lines = [
        "THE LAWS OF THE GAME (IFAB 2025/26) — READ THESE BEFORE JUDGING THE CLIP.",
        "You must map your verdict to specific Laws and cite them (e.g. 'Law 12.1').",
    ]
    lines.append("")
    lines.append("LAW DIGEST:")
    for entry in LAWS_DIGEST:
        lines.append(f"[{entry['law']}] {entry['title']}")
        for point in entry["points"]:
            lines.append(f"  - {point}")
    lines.append("")
    lines.append(f"COMPETITION: {competition}")
    for note in COMPETITION_NOTES.get(competition, COMPETITION_NOTES.get("Other", [])):
        lines.append(f"  - {note}")
    if decision_type and decision_type != "auto":
        lines.append("")
        lines.append(
            f"USER INDICATED THE DECISION TYPE IS: {decision_type.upper()}. "
            "Focus your review on the Laws that govern that decision."
        )
    lines.append("")
    lines.append(
        "In every reasoning step and every key-frame caption, cite the Law you are applying. "
        "If you cannot determine the correct Law from the visible footage, say the footage is inconclusive."
    )
    return "\n".join(lines)
