"""Schemas for Slay the Spire 2 graph state."""

from typing import (
    Annotated,
    Any,
    Literal,
    Optional,
)

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)


CardType = Literal["attack", "skill", "power", "status", "curse"]
CardRarity = Literal["basic", "common", "uncommon", "rare", "ancient", "event", "special"]
CardOwner = Literal["ironclad", "silent", "regent", "necrobinder", "defect", "colorless"]
TargetType = Literal["self", "enemy", "all_enemies", "ally", "all_allies", "none"]
ChoiceType = Literal["card_reward", "map_path", "shop_buy", "event_select", "combat_turn", "rest_site"]
ModeType = Literal["assist"]


class CardValueCurve(BaseModel):
    """Represents a value that can vary by upgrade level."""

    base: Optional[float] = Field(default=None, description="Base value at upgrade level 0")
    by_upgrade: dict[int, float] = Field(
        default_factory=dict,
        description="Value overrides keyed by upgrade level",
    )


class EffectSpec(BaseModel):
    """Structured effect specification for card behavior."""

    op: str = Field(..., description="Effect operation identifier")
    target: TargetType = Field(default="none", description="Target selection for the effect")
    amount: Optional[CardValueCurve] = Field(default=None, description="Numeric amount of the effect")
    count: Optional[CardValueCurve] = Field(default=None, description="Repeat count for the effect")
    status_key: Optional[str] = Field(default=None, description="Status or power identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional effect-specific metadata")


class CardVersion(BaseModel):
    """Versioned card properties per upgrade level."""

    level: int = Field(..., ge=0, description="Upgrade level where 0 is base")
    cost: Optional[int] = Field(default=None, ge=0, description="Card cost for this version, if fixed")
    raw_text: str = Field(default="", description="Raw rules text for this version")
    keywords: list[str] = Field(default_factory=list, description="Keywords present in this version")
    effects: list[EffectSpec] = Field(default_factory=list, description="Structured effects for this version")


class STSCardDef(BaseModel):
    """Static card definition sourced from a card catalog."""

    card_id: str = Field(..., description="Stable unique card id")
    name: str = Field(..., description="Display name")
    owner: CardOwner = Field(..., description="Owning character or colorless pool")
    card_type: CardType = Field(..., description="Card type")
    rarity: CardRarity = Field(..., description="Card rarity")
    tags: list[str] = Field(default_factory=list, description="Extra source tags such as token or quest")
    upgradable: bool = Field(default=True, description="Whether this card can be upgraded")
    max_upgrade_level: int = Field(default=1, ge=0, description="Maximum supported upgrade level")
    versions: list[CardVersion] = Field(default_factory=list, description="Version snapshots by upgrade level")


class STSCardInstance(BaseModel):
    """Run-scoped card instance stored in deck and piles."""

    instance_id: str = Field(..., description="Unique card instance id")
    card_id: str = Field(..., description="Reference to STSCardDef.card_id")
    upgrade_level: int = Field(default=0, ge=0, description="Current upgrade level")
    enchants: list[str] = Field(default_factory=list, description="Enchantment identifiers attached to this card")
    permanent_mods: dict[str, Any] = Field(default_factory=dict, description="Permanent modifications on this card")
    generated_by: Optional[str] = Field(default=None, description="Source that generated this card instance")
    ephemeral: bool = Field(default=False, description="Whether the card disappears after combat")


class STSCardRuntime(BaseModel):
    """Combat-scoped runtime properties for a card instance."""

    instance_id: str = Field(..., description="Reference to STSCardInstance.instance_id")
    zone: Literal["draw", "hand", "discard", "exhaust", "limbo", "removed"] = Field(
        default="draw",
        description="Current zone of the card",
    )
    current_cost: Optional[int] = Field(default=None, ge=0, description="Resolved cost this turn")
    playable: bool = Field(default=True, description="Whether the card is currently playable")
    resolved_effects: list[EffectSpec] = Field(default_factory=list, description="Effects after runtime modifiers")
    runtime_flags: list[str] = Field(default_factory=list, description="Runtime flags such as free_this_turn")


class STSRunMeta(BaseModel):
    """Metadata for identifying and segmenting a run."""

    run_id: str = Field(..., description="Unique run id")
    character: CardOwner = Field(..., description="Character used in this run")
    ascension: int = Field(default=0, ge=0, le=20, description="Ascension level")
    act: int = Field(default=1, ge=1, le=4, description="Current act")
    floor: int = Field(default=1, ge=1, description="Current floor")
    seed: Optional[str] = Field(default=None, description="Game seed")
    map_node_id: Optional[str] = Field(default=None, description="Current map node id")


class STSPlayerState(BaseModel):
    """Player status and resources for decision making."""

    hp: int = Field(..., ge=0, description="Current health")
    max_hp: int = Field(..., ge=1, description="Maximum health")
    block: int = Field(default=0, ge=0, description="Current block")
    gold: int = Field(default=0, ge=0, description="Current gold")
    resources: dict[str, int] = Field(
        default_factory=dict,
        description="Character-specific resources such as energy, stars, or summon",
    )
    powers: dict[str, int] = Field(default_factory=dict, description="Active power stacks")
    potions: list[str] = Field(default_factory=list, description="Potion ids currently held")


class STSEnemyIntent(BaseModel):
    """Enemy intent summary used for tactical planning."""

    enemy_id: str = Field(..., description="Stable enemy id")
    name: str = Field(..., description="Display name")
    hp: int = Field(..., ge=0, description="Current enemy health")
    block: int = Field(default=0, ge=0, description="Current enemy block")
    intent: str = Field(..., description="Intent description")
    intent_metadata: dict[str, Any] = Field(default_factory=dict, description="Structured intent payload")


class STSCombatState(BaseModel):
    """Combat snapshot for turn-level planning."""

    in_combat: bool = Field(default=False, description="Whether combat is active")
    turn: int = Field(default=0, ge=0, description="Current combat turn")
    enemies: list[STSEnemyIntent] = Field(default_factory=list, description="Enemy intents and stats")
    hand_instance_ids: list[str] = Field(default_factory=list, description="Instance ids currently in hand")
    draw_pile_count: int = Field(default=0, ge=0, description="Number of cards in draw pile")
    discard_pile_count: int = Field(default=0, ge=0, description="Number of cards in discard pile")
    exhaust_pile_count: int = Field(default=0, ge=0, description="Number of cards in exhaust pile")


class STSChoiceOption(BaseModel):
    """Single option in a decision prompt."""

    option_id: str = Field(..., description="Stable option id")
    label: str = Field(..., description="Display text for the option")
    option_type: str = Field(..., description="Category of choice option")
    payload: dict[str, Any] = Field(default_factory=dict, description="Structured option details")


class STSChoiceContext(BaseModel):
    """Current decision context received from the game state."""

    choice_type: ChoiceType = Field(..., description="Type of decision required")
    options: list[STSChoiceOption] = Field(default_factory=list, description="Available options")
    constraints: dict[str, Any] = Field(default_factory=dict, description="Hard constraints for selection")


class STSDecision(BaseModel):
    """Agent output for decision support and autoplay."""

    chosen_option_id: Optional[str] = Field(default=None, description="Selected option id")
    reasoning: str = Field(default="", description="Short explanation for the choice")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    risk_tags: list[str] = Field(default_factory=list, description="Risk labels for human review")
    candidate_rankings: list[str] = Field(default_factory=list, description="Ranked alternative option ids")


class STSAssistGraphState(BaseModel):
    """Graph state for STS2 assistant workflows."""

    mode: ModeType = Field(default="assist", description="Workflow mode")
    messages: Annotated[list, add_messages] = Field(default_factory=list, description="Conversation messages")
    run_meta: STSRunMeta
    player: STSPlayerState
    deck: list[STSCardInstance] = Field(default_factory=list, description="Persistent deck composition")
    card_runtime: list[STSCardRuntime] = Field(default_factory=list, description="Combat runtime card snapshots")
    combat: STSCombatState = Field(default_factory=STSCombatState, description="Current combat snapshot")
    choice_context: Optional[STSChoiceContext] = Field(default=None, description="Current unresolved decision")
    decision: Optional[STSDecision] = Field(default=None, description="Most recent model decision")
    ui_context: dict[str, Any] = Field(default_factory=dict, description="Optional UI context from the helper mod")
    long_term_memory: str = Field(default="", description="Persistent user strategy memory")


class STSGraphState(STSAssistGraphState):
    """Backward-compatible alias for existing imports."""
