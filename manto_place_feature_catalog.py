"""Reader-facing definitions for the MANTO connectedness feature set."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaceSurvivalFeature:
    """Documentation metadata for one place-survival model feature."""

    name: str
    title: str
    category: str
    definition: str
    calculation: str
    higher_value: str
    caution: str
    value_kind: str = "count"
    related_features: tuple[str, ...] = ()
    missing_sentinel: float | None = None
    missing_label: str = ""

    @property
    def slug(self) -> str:
        return self.name.replace("_", "-")


FEATURE_CATALOG = (
    PlaceSurvivalFeature(
        name="place_graph_degree",
        title="Place Graph Degree",
        category="Place neighbourhood",
        definition=(
            "The number of distinct places directly connected to the focal place "
            "in the pre-Pausanias MANTO place graph."
        ),
        calculation=(
            "Build an undirected graph from eligible place-to-place MANTO "
            "relationships, add each place's somewhere-in-or-near parent relation, "
            "and count the focal node's distinct adjacent place nodes."
        ),
        higher_value=(
            "The place has direct narrative or containment links to more places."
        ),
        caution=(
            "Degree counts distinct neighbouring places, not the number of stories "
            "or the geographic closeness of those places."
        ),
        related_features=(
            "place_graph_pagerank",
            "direct_place_neighbor_count",
            "local_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="place_graph_pagerank",
        title="Place Graph PageRank",
        category="Place neighbourhood",
        definition=(
            "A weighted network-centrality score for the focal place in the "
            "pre-Pausanias MANTO place graph."
        ),
        calculation=(
            "Run PageRank on the undirected place graph. Repeated eligible MANTO "
            "relationships between a pair of places increase that edge's weight."
        ),
        higher_value=(
            "The place is connected to other well-connected places through stronger "
            "or repeated place-to-place ties."
        ),
        caution=(
            "PageRank is relative to the imported graph and release. It is not a "
            "measure of population, political importance, or textual frequency in "
            "Pausanias."
        ),
        value_kind="decimal",
        related_features=(
            "place_graph_degree",
            "large_place_max_pagerank",
            "has_large_place_neighbor",
        ),
    ),
    PlaceSurvivalFeature(
        name="local_place_neighbor_count",
        title="Local Place Neighbor Count",
        category="Place neighbourhood",
        definition=(
            "The number of distinct operational neighbours assigned to the focal "
            "place."
        ),
        calculation=(
            "Take the union of direct place-graph neighbours and places sharing the "
            "same MANTO parent locality; include the parent itself when it is a "
            "place node, then remove the focal place."
        ),
        higher_value=(
            "The place sits in a larger MANTO narrative or locality neighbourhood."
        ),
        caution=(
            "“Local” is an operational graph term. It combines MANTO relations and "
            "containment structure; it does not mean within a fixed geographic "
            "distance."
        ),
        related_features=(
            "direct_place_neighbor_count",
            "same_parent_place_neighbor_count",
            "large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="direct_place_neighbor_count",
        title="Direct Place Neighbor Count",
        category="Place neighbourhood",
        definition=(
            "The number of distinct places joined directly to the focal place in "
            "the constructed place graph."
        ),
        calculation=(
            "Count adjacent place nodes created from eligible MANTO place-to-place "
            "relationships, including the constructed somewhere-in-or-near edge "
            "between a place and its recorded parent locality."
        ),
        higher_value=(
            "The focal place has direct graph ties to more other places."
        ),
        caution=(
            "A direct graph tie can be narrative or hierarchical. It need not be a "
            "road, border, or measured geographic adjacency."
        ),
        related_features=(
            "place_graph_degree",
            "same_parent_place_neighbor_count",
            "strong_place_tie_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="same_parent_place_neighbor_count",
        title="Same-Parent Place Neighbor Count",
        category="Place neighbourhood",
        definition=(
            "The number of places connected to the focal place through MANTO's "
            "parent-locality structure."
        ),
        calculation=(
            "Count sibling places that share the focal place's parent, and include "
            "the parent itself when the parent is represented as a place node."
        ),
        higher_value=(
            "The focal place belongs to a parent locality containing more recorded "
            "places."
        ),
        caution=(
            "The count depends on the completeness and granularity of MANTO's "
            "containment hierarchy."
        ),
        related_features=(
            "local_place_neighbor_count",
            "direct_place_neighbor_count",
            "large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="large_place_neighbor_count",
        title="Large-Place Neighbor Count",
        category="Large-place connections",
        definition=(
            "The number of operational neighbours classified as large network "
            "places."
        ),
        calculation=(
            "Identify places in the top configured quantile for either graph degree "
            "or PageRank, then count how many of the focal place's local neighbours "
            "belong to that set."
        ),
        higher_value=(
            "The place has ties to more highly connected places in the MANTO graph."
        ),
        caution=(
            "“Large” means network-prominent under the configured threshold, not "
            "physically large or historically populous."
        ),
        related_features=(
            "has_large_place_neighbor",
            "large_place_max_degree",
            "large_place_max_pagerank",
        ),
    ),
    PlaceSurvivalFeature(
        name="large_place_max_degree",
        title="Maximum Degree of a Large-Place Neighbor",
        category="Large-place connections",
        definition=(
            "The largest graph-degree value found among the focal place's large "
            "operational neighbours."
        ),
        calculation=(
            "For local neighbours that meet the large-place threshold, take the "
            "maximum place-graph degree; use zero when there is no such neighbour."
        ),
        higher_value=(
            "At least one neighbouring large place has more distinct graph ties."
        ),
        caution=(
            "This is controlled by a single neighbour and can move when the MANTO "
            "network or large-place threshold changes."
        ),
        related_features=(
            "large_place_neighbor_count",
            "large_place_max_pagerank",
            "place_graph_degree",
        ),
    ),
    PlaceSurvivalFeature(
        name="large_place_max_pagerank",
        title="Maximum PageRank of a Large-Place Neighbor",
        category="Large-place connections",
        definition=(
            "The largest PageRank score found among the focal place's large "
            "operational neighbours."
        ),
        calculation=(
            "For local neighbours that meet the large-place threshold, take the "
            "maximum weighted place-graph PageRank; use zero when none qualify."
        ),
        higher_value=(
            "The focal place is connected to at least one more-central large place."
        ),
        caution=(
            "The score is relative to this release's graph and may be dominated by "
            "one neighbour."
        ),
        value_kind="decimal",
        related_features=(
            "large_place_neighbor_count",
            "large_place_max_degree",
            "place_graph_pagerank",
        ),
    ),
    PlaceSurvivalFeature(
        name="has_large_place_neighbor",
        title="Has a Large-Place Neighbor",
        category="Large-place connections",
        definition=(
            "A yes/no indicator showing whether the focal place has at least one "
            "operational neighbour classified as a large network place."
        ),
        calculation=(
            "Set the feature to yes when large-place neighbor count is greater than "
            "zero; otherwise set it to no."
        ),
        higher_value=(
            "A value of one means at least one large-place connection is present."
        ),
        caution=(
            "This discards the number and strength of large-place connections; the "
            "companion count and maximum features retain that detail."
        ),
        value_kind="boolean",
        related_features=(
            "large_place_neighbor_count",
            "large_place_max_degree",
            "large_place_max_pagerank",
        ),
    ),
    PlaceSurvivalFeature(
        name="strong_place_tie_count",
        title="Strong Place Tie Count",
        category="Large-place connections",
        definition=(
            "The number of large direct neighbours connected by a selected strong "
            "place-to-place relationship."
        ),
        calculation=(
            "Among direct neighbours that meet the large-place threshold, count "
            "those joined by at least one relation such as founded from, settled "
            "from, conquered by, destroyed by, fortified by, belongs to, ruled by, "
            "or ruler of."
        ),
        higher_value=(
            "The place has strong narrative or political ties to more large places."
        ),
        caution=(
            "The feature uses a curated relation list and counts qualifying "
            "neighbouring places, not relation occurrences."
        ),
        related_features=(
            "direct_place_neighbor_count",
            "large_place_neighbor_count",
            "kin_linked_large_place_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="mythic_figure_count",
        title="Mythic Figure Count",
        category="Figures and their reach",
        definition=(
            "The number of distinct MANTO person entities associated with the "
            "focal place."
        ),
        calculation=(
            "Collect person entities from eligible place-to-person or "
            "person-to-place relationships and count each distinct person once."
        ),
        higher_value=(
            "More distinct mythic figures are attached to the place."
        ),
        caution=(
            "This measures distinct linked figures, not their story frequency or "
            "importance."
        ),
        related_features=(
            "exclusive_figure_count",
            "panhellenic_figure_count",
            "figure_mean_ubiquity",
        ),
    ),
    PlaceSurvivalFeature(
        name="action_pattern_count",
        title="Action Pattern Count",
        category="Action profiles",
        definition=(
            "The number of distinct canonical action categories represented among "
            "the focal place's figure relationships."
        ),
        calculation=(
            "Map eligible MANTO relations to categories such as foundation, burial, "
            "cult site, rule, destruction, games, or settlement, then count the "
            "distinct categories present."
        ),
        higher_value=(
            "The place participates in a more varied set of mythic action types."
        ),
        caution=(
            "Multiple relations mapped to the same canonical action count once, so "
            "this measures variety rather than volume."
        ),
        related_features=(
            "action_profile_entropy",
            "shared_action_pattern_count",
            "mythic_figure_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_mythic_figure_neighbor_count",
        title="Shared-Mythic-Figure Neighbor Count",
        category="Shared figures",
        definition=(
            "The number of operational neighbours that share at least one mythic "
            "figure with the focal place."
        ),
        calculation=(
            "For each local neighbour, intersect its distinct person set with the "
            "focal place's person set and count the neighbour once when the "
            "intersection is non-empty."
        ),
        higher_value=(
            "The place shares figures with more members of its neighbourhood."
        ),
        caution=(
            "A neighbour counts once whether it shares one figure or many; companion "
            "features capture the number of figures."
        ),
        related_features=(
            "shared_mythic_figure_count",
            "max_shared_mythic_figures_with_neighbor",
            "shared_figure_neighbor_zscore",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_mythic_figure_count",
        title="Shared Mythic Figure Count",
        category="Shared figures",
        definition=(
            "The number of distinct mythic figures shared between the focal place "
            "and at least one operational neighbour."
        ),
        calculation=(
            "Take the union of all focal-place figures found in each local "
            "neighbour's figure set, then count the distinct figures."
        ),
        higher_value=(
            "More of the focal place's figures also occur in its neighbourhood."
        ),
        caution=(
            "A widely shared figure still counts once, regardless of how many "
            "neighbours contain that figure."
        ),
        related_features=(
            "shared_mythic_figure_neighbor_count",
            "max_shared_mythic_figures_with_neighbor",
            "shared_figure_count_zscore",
        ),
    ),
    PlaceSurvivalFeature(
        name="max_shared_mythic_figures_with_neighbor",
        title="Maximum Shared Mythic Figures with One Neighbor",
        category="Shared figures",
        definition=(
            "The largest number of mythic figures shared with any single "
            "operational neighbour."
        ),
        calculation=(
            "Count the figure-set intersection for every local neighbour and keep "
            "the largest count; use zero when there are no shared figures."
        ),
        higher_value=(
            "The focal place has a particularly figure-rich tie to at least one "
            "neighbour."
        ),
        caution=(
            "This maximum can be driven by one pair of places and does not describe "
            "the rest of the neighbourhood."
        ),
        related_features=(
            "shared_mythic_figure_count",
            "shared_mythic_figure_neighbor_count",
            "shared_mythic_figure_large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_mythic_figure_large_place_neighbor_count",
        title="Shared-Figure Large-Place Neighbor Count",
        category="Shared figures",
        definition=(
            "The number of large operational neighbours that share at least one "
            "mythic figure with the focal place."
        ),
        calculation=(
            "Count local neighbours that both meet the large-place threshold and "
            "have a non-empty figure-set intersection with the focal place."
        ),
        higher_value=(
            "The place shares figures with more network-prominent neighbours."
        ),
        caution=(
            "The result depends on both the operational-neighbour definition and "
            "the release-specific large-place threshold."
        ),
        related_features=(
            "shared_mythic_figure_neighbor_count",
            "large_place_neighbor_count",
            "shared_action_large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_action_neighbor_count",
        title="Shared-Action Neighbor Count",
        category="Shared action patterns",
        definition=(
            "The number of operational neighbours sharing at least one canonical "
            "action pattern with the focal place through different figures."
        ),
        calculation=(
            "For each local neighbour, find canonical action categories present on "
            "both sides. Retain a category only when each place has at least one "
            "figure not used for that action at the other place, then count "
            "qualifying neighbours."
        ),
        higher_value=(
            "More neighbours participate in comparable action types through "
            "distinct local casts of figures."
        ),
        caution=(
            "The distinct-figure rule deliberately excludes a shared action "
            "explained only by the same travelling figure at both places."
        ),
        related_features=(
            "shared_action_pattern_count",
            "shared_action_neighbor_pattern_count",
            "shared_action_large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_action_pattern_count",
        title="Shared Action Pattern Count",
        category="Shared action patterns",
        definition=(
            "The number of distinct canonical action categories shared with at "
            "least one operational neighbour through different figures."
        ),
        calculation=(
            "Apply the distinct-figure shared-action rule to every local neighbour, "
            "take the union of qualifying canonical action categories, and count "
            "them."
        ),
        higher_value=(
            "A wider variety of the focal place's action types is echoed elsewhere "
            "in its neighbourhood."
        ),
        caution=(
            "Each action category counts once overall even if it is shared with "
            "many neighbours."
        ),
        related_features=(
            "shared_action_neighbor_count",
            "shared_action_neighbor_pattern_count",
            "action_pattern_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_action_neighbor_pattern_count",
        title="Shared Action Neighbor-Pattern Count",
        category="Shared action patterns",
        definition=(
            "The total number of qualifying neighbour-by-action combinations."
        ),
        calculation=(
            "For each local neighbour, count canonical action categories that pass "
            "the distinct-figure shared-action rule, then sum those counts across "
            "all neighbours."
        ),
        higher_value=(
            "The place has more repeated action-pattern connections across its "
            "neighbourhood."
        ),
        caution=(
            "Unlike shared action pattern count, the same action contributes again "
            "when it is shared with another neighbour."
        ),
        related_features=(
            "shared_action_neighbor_count",
            "shared_action_pattern_count",
            "max_shared_action_patterns_with_neighbor",
        ),
    ),
    PlaceSurvivalFeature(
        name="max_shared_action_patterns_with_neighbor",
        title="Maximum Shared Action Patterns with One Neighbor",
        category="Shared action patterns",
        definition=(
            "The largest number of qualifying canonical action categories shared "
            "with any single operational neighbour."
        ),
        calculation=(
            "Apply the distinct-figure shared-action rule to each local neighbour "
            "and keep the largest number of qualifying action categories."
        ),
        higher_value=(
            "At least one neighbour has a more similar, but not figure-identical, "
            "action repertoire."
        ),
        caution=(
            "The maximum can be dominated by one pair and does not show how broadly "
            "the pattern is distributed."
        ),
        related_features=(
            "shared_action_pattern_count",
            "shared_action_neighbor_pattern_count",
            "max_action_cosine_with_neighbor",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_action_large_place_neighbor_count",
        title="Shared-Action Large-Place Neighbor Count",
        category="Shared action patterns",
        definition=(
            "The number of large operational neighbours sharing at least one "
            "qualifying canonical action pattern with the focal place."
        ),
        calculation=(
            "Count local neighbours that meet the large-place threshold and pass "
            "the distinct-figure shared-action rule for at least one action "
            "category."
        ),
        higher_value=(
            "The place shares action types with more network-prominent neighbours."
        ),
        caution=(
            "The feature combines two constructed thresholds: large-place status "
            "and the distinct-figure shared-action rule."
        ),
        related_features=(
            "shared_action_neighbor_count",
            "large_place_neighbor_count",
            "shared_mythic_figure_large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="exclusive_figure_count",
        title="Exclusive Figure Count",
        category="Figures and their reach",
        definition=(
            "The number of the focal place's mythic figures that occur at no other "
            "place in the imported pre-Pausanias network."
        ),
        calculation=(
            "Count how many distinct figures attached to the focal place have a "
            "global place-association count of exactly one."
        ),
        higher_value=(
            "The place has more figures unique to it within the imported network."
        ),
        caution=(
            "“Exclusive” is relative to the current MANTO release and source-date "
            "filter; missing evidence can make a figure appear more local."
        ),
        related_features=(
            "mythic_figure_count",
            "panhellenic_figure_count",
            "figure_mean_ubiquity",
        ),
    ),
    PlaceSurvivalFeature(
        name="panhellenic_figure_count",
        title="Panhellenic Figure Count",
        category="Figures and their reach",
        definition=(
            "The number of the focal place's mythic figures associated with at "
            "least the configured number of places across the network."
        ),
        calculation=(
            "Count focal-place figures whose global place-association count reaches "
            "the configured threshold, currently ten places."
        ),
        higher_value=(
            "The place is associated with more widely distributed mythic figures."
        ),
        caution=(
            "The term “Panhellenic” is an operational threshold label, not a claim "
            "about cult status or ancient reception."
        ),
        related_features=(
            "exclusive_figure_count",
            "figure_mean_ubiquity",
            "figure_max_ubiquity",
        ),
    ),
    PlaceSurvivalFeature(
        name="figure_mean_ubiquity",
        title="Mean Figure Ubiquity",
        category="Figures and their reach",
        definition=(
            "The average number of places associated with each mythic figure at "
            "the focal place."
        ),
        calculation=(
            "For every focal-place figure, count its distinct associated places "
            "across the network and take the arithmetic mean; use zero when the "
            "place has no figures."
        ),
        higher_value=(
            "The place's typical figure appears across more places."
        ),
        caution=(
            "A mean can obscure a mixture of very local and very widespread "
            "figures; compare it with the maximum and exclusive-figure count."
        ),
        value_kind="decimal",
        related_features=(
            "figure_max_ubiquity",
            "exclusive_figure_count",
            "panhellenic_figure_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="figure_max_ubiquity",
        title="Maximum Figure Ubiquity",
        category="Figures and their reach",
        definition=(
            "The largest number of places associated with any one mythic figure at "
            "the focal place."
        ),
        calculation=(
            "Count each focal-place figure's distinct associated places and keep "
            "the largest value; use zero when the place has no figures."
        ),
        higher_value=(
            "At least one figure attached to the place is more widely distributed."
        ),
        caution=(
            "The value can be driven by a single exceptionally widespread figure."
        ),
        related_features=(
            "figure_mean_ubiquity",
            "panhellenic_figure_count",
            "mythic_figure_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="kin_linked_place_count",
        title="Kin-Linked Place Count",
        category="Kinship connections",
        definition=(
            "The number of distinct places connected genealogically to the focal "
            "place through its mythic figures."
        ),
        calculation=(
            "For each focal-place figure, find its person-to-person kin in MANTO, "
            "exclude kin who are themselves focal-place figures, collect all other "
            "places associated with those kin, remove the focal place, and count "
            "the distinct places."
        ),
        higher_value=(
            "The families of the focal place's figures extend to more other places."
        ),
        caution=(
            "This measures a two-step person-kin-person-to-place path. It does not "
            "require the resulting places to be local neighbours."
        ),
        related_features=(
            "kin_linked_neighbor_count",
            "kin_linked_large_place_count",
            "mythic_figure_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="kin_linked_neighbor_count",
        title="Kin-Linked Neighbor Count",
        category="Kinship connections",
        definition=(
            "The number of operational neighbours connected genealogically to the "
            "focal place through different mythic figures."
        ),
        calculation=(
            "Construct the kin-linked place set from two-step figure-to-kin-to-place "
            "paths, excluding kin already attached to the focal place, then count "
            "how many of those places are also in the focal place's operational "
            "neighbour set."
        ),
        higher_value=(
            "More neighbours host kin of figures associated with the focal place."
        ),
        caution=(
            "Each neighbouring place counts once even when several kinship paths "
            "connect it. “Neighbour” is graph/locality based, not a distance band."
        ),
        related_features=(
            "kin_linked_place_count",
            "kin_linked_large_place_count",
            "local_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="kin_linked_large_place_count",
        title="Kin-Linked Large-Place Count",
        category="Kinship connections",
        definition=(
            "The number of network-prominent places connected genealogically to "
            "the focal place through different mythic figures."
        ),
        calculation=(
            "Construct the kin-linked place set from figure-to-kin-to-place paths "
            "and count how many resulting places meet the large-place threshold."
        ),
        higher_value=(
            "The families of focal-place figures extend to more network-prominent "
            "places."
        ),
        caution=(
            "A kin-linked large place need not be an operational neighbour of the "
            "focal place."
        ),
        related_features=(
            "kin_linked_place_count",
            "kin_linked_neighbor_count",
            "large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="action_profile_entropy",
        title="Action Profile Entropy",
        category="Action profiles",
        definition=(
            "A Shannon-entropy measure of how evenly the focal place's figure "
            "relationships are distributed across canonical action categories."
        ),
        calculation=(
            "Count distinct figures in each action category, convert the counts to "
            "shares, and calculate base-two Shannon entropy. Empty or one-category "
            "profiles receive zero."
        ),
        higher_value=(
            "The action profile is more varied and more evenly spread across "
            "categories."
        ),
        caution=(
            "Entropy combines variety and evenness; two places with the same value "
            "can have different action categories."
        ),
        value_kind="decimal",
        related_features=(
            "action_pattern_count",
            "max_action_cosine_with_neighbor",
            "mean_action_cosine_with_neighbors",
        ),
    ),
    PlaceSurvivalFeature(
        name="max_action_cosine_with_neighbor",
        title="Maximum Action Cosine with a Neighbor",
        category="Action profiles",
        definition=(
            "The highest cosine similarity between the focal place's action-count "
            "profile and that of any operational neighbour."
        ),
        calculation=(
            "Represent each place as counts of figures by canonical action category, "
            "calculate cosine similarity with every local neighbour, and retain the "
            "maximum; empty profiles contribute zero."
        ),
        higher_value=(
            "At least one neighbour has a more proportionally similar action "
            "profile."
        ),
        caution=(
            "The maximum describes the closest single match and can conceal a very "
            "different remaining neighbourhood."
        ),
        value_kind="decimal",
        related_features=(
            "mean_action_cosine_with_neighbors",
            "max_action_cosine_with_large_place",
            "action_profile_entropy",
        ),
    ),
    PlaceSurvivalFeature(
        name="mean_action_cosine_with_neighbors",
        title="Mean Action Cosine with Neighbors",
        category="Action profiles",
        definition=(
            "The average cosine similarity between the focal place's action-count "
            "profile and those of all operational neighbours."
        ),
        calculation=(
            "Calculate action-profile cosine similarity for every local neighbour "
            "and take the arithmetic mean; neighbours with empty profiles contribute "
            "zero, and places with no neighbours receive zero."
        ),
        higher_value=(
            "The focal place's action profile is more consistently similar to its "
            "neighbourhood."
        ),
        caution=(
            "The mean is affected by neighbours with no recorded action profile and "
            "therefore partly reflects MANTO coverage."
        ),
        value_kind="decimal",
        related_features=(
            "max_action_cosine_with_neighbor",
            "max_action_cosine_with_large_place",
            "action_profile_entropy",
        ),
    ),
    PlaceSurvivalFeature(
        name="max_action_cosine_with_large_place",
        title="Maximum Action Cosine with a Large Place",
        category="Action profiles",
        definition=(
            "The highest action-profile cosine similarity between the focal place "
            "and any large operational neighbour."
        ),
        calculation=(
            "Calculate action-profile cosine similarity only for local neighbours "
            "meeting the large-place threshold and retain the maximum; use zero "
            "when none qualify."
        ),
        higher_value=(
            "At least one network-prominent neighbour has a more similar action "
            "profile."
        ),
        caution=(
            "The feature combines profile similarity with release-specific "
            "large-place classification and may be driven by one neighbour."
        ),
        value_kind="decimal",
        related_features=(
            "max_action_cosine_with_neighbor",
            "mean_action_cosine_with_neighbors",
            "large_place_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="archaic_story_count",
        title="Archaic Attestation Count",
        category="Temporal evidence",
        definition=(
            "The number of eligible dated MANTO relationship edges involving the "
            "focal place whose latest evidence date is 480 BCE or earlier."
        ),
        calculation=(
            "For each eligible edge touching the place, inspect "
            "evidence_latest_year and count it in the archaic stratum when the year "
            "is at most −480."
        ),
        higher_value=(
            "More place-related MANTO edges have evidence securely ending in the "
            "archaic stratum."
        ),
        caution=(
            "Despite the stored feature name, this counts dated relationship edges, "
            "not independently reconstructed stories."
        ),
        related_features=(
            "classical_story_count",
            "earliest_attestation_year",
            "attestation_span_years",
        ),
    ),
    PlaceSurvivalFeature(
        name="classical_story_count",
        title="Classical Attestation Count",
        category="Temporal evidence",
        definition=(
            "The number of eligible dated MANTO relationship edges involving the "
            "focal place whose latest evidence date falls from 479 to 323 BCE."
        ),
        calculation=(
            "Count eligible edges touching the place when evidence_latest_year is "
            "between −479 and −323 inclusive."
        ),
        higher_value=(
            "More place-related MANTO edges are attested within the classical "
            "stratum."
        ),
        caution=(
            "This counts relationship edges by their latest evidence date and is "
            "sensitive to source dating and database coverage."
        ),
        related_features=(
            "archaic_story_count",
            "hellenistic_story_count",
            "latest_attestation_year",
        ),
    ),
    PlaceSurvivalFeature(
        name="hellenistic_story_count",
        title="Hellenistic Attestation Count",
        category="Temporal evidence",
        definition=(
            "The number of eligible dated MANTO relationship edges involving the "
            "focal place whose latest evidence date falls from 322 to 31 BCE."
        ),
        calculation=(
            "Count eligible edges touching the place when evidence_latest_year is "
            "between −322 and −31 inclusive."
        ),
        higher_value=(
            "More place-related MANTO edges are attested within the Hellenistic "
            "stratum."
        ),
        caution=(
            "This is a count of dated relationship edges, not an independent count "
            "of historical events."
        ),
        related_features=(
            "classical_story_count",
            "early_imperial_story_count",
            "attestation_span_years",
        ),
    ),
    PlaceSurvivalFeature(
        name="early_imperial_story_count",
        title="Early Imperial Attestation Count",
        category="Temporal evidence",
        definition=(
            "The number of eligible dated MANTO relationship edges involving the "
            "focal place whose latest evidence date falls from 30 BCE through "
            "170 CE."
        ),
        calculation=(
            "Count eligible edges touching the place when evidence_latest_year is "
            "between −30 and 170 inclusive. The model-facing import still enforces "
            "the strict pre-Pausanias evidence policy."
        ),
        higher_value=(
            "More place-related MANTO edges are attested in the permitted early "
            "imperial stratum."
        ),
        caution=(
            "This is close to Pausanias's period and therefore depends especially "
            "on conservative source dating; Pausanias-derived edges remain excluded."
        ),
        related_features=(
            "hellenistic_story_count",
            "latest_attestation_year",
            "attestation_span_years",
        ),
    ),
    PlaceSurvivalFeature(
        name="earliest_attestation_year",
        title="Earliest Attestation Year",
        category="Temporal evidence",
        definition=(
            "The earliest latest-evidence year among eligible dated MANTO "
            "relationships involving the focal place."
        ),
        calculation=(
            "Take the minimum evidence_latest_year across eligible edges touching "
            "the place. BCE years are negative. Places with no dated edge use the "
            "internal sentinel 200 and are reported separately on this page."
        ),
        higher_value=(
            "Among attested places, a higher value means the earliest available "
            "evidence is later in time."
        ),
        caution=(
            "The measure uses each edge's latest admissible evidence date, not "
            "necessarily the date when a tradition originated."
        ),
        value_kind="year",
        related_features=(
            "latest_attestation_year",
            "attestation_span_years",
            "archaic_story_count",
        ),
        missing_sentinel=200,
        missing_label="No eligible dated attestation",
    ),
    PlaceSurvivalFeature(
        name="latest_attestation_year",
        title="Latest Attestation Year",
        category="Temporal evidence",
        definition=(
            "The latest evidence year among eligible dated MANTO relationships "
            "involving the focal place."
        ),
        calculation=(
            "Take the maximum evidence_latest_year across eligible edges touching "
            "the place. BCE years are negative. Places with no dated edge use the "
            "internal sentinel −1400 and are reported separately on this page."
        ),
        higher_value=(
            "Among attested places, a higher value means evidence continues closer "
            "to Pausanias's period."
        ),
        caution=(
            "This records the latest eligible source date represented in MANTO, not "
            "the historical end of a place or tradition."
        ),
        value_kind="year",
        related_features=(
            "earliest_attestation_year",
            "attestation_span_years",
            "early_imperial_story_count",
        ),
        missing_sentinel=-1400,
        missing_label="No eligible dated attestation",
    ),
    PlaceSurvivalFeature(
        name="attestation_span_years",
        title="Attestation Span in Years",
        category="Temporal evidence",
        definition=(
            "The number of years between the earliest and latest eligible dated "
            "MANTO relationships involving the focal place."
        ),
        calculation=(
            "Subtract earliest_attestation_year from latest_attestation_year for "
            "places with dated evidence; use zero for an unattested place."
        ),
        higher_value=(
            "The imported evidence for the place spans a longer period."
        ),
        caution=(
            "A zero can mean either one dated point or no dated evidence, so it must "
            "be read with the earliest and latest features."
        ),
        value_kind="years",
        related_features=(
            "earliest_attestation_year",
            "latest_attestation_year",
            "archaic_story_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_figure_count_zscore",
        title="Shared Figure Count Z-Score",
        category="Null-model comparisons",
        definition=(
            "How unusual the focal place's distinct shared-figure count is relative "
            "to degree-preserving randomised place–figure networks."
        ),
        calculation=(
            "Randomly reassign figure incidences while preserving every place's "
            "figure count and every figure's overall ubiquity, keep neighbourhoods "
            "fixed, and recompute distinct shared figures. Subtract the null mean "
            "from the observed count and divide by the null standard deviation. "
            "The current feature build uses 20 seeded rewiring samples."
        ),
        higher_value=(
            "The place shares more distinct figures with its neighbours than the "
            "null model expects."
        ),
        caution=(
            "A value of zero is also used when the sampled null distribution has "
            "zero variance. With 20 samples, the estimate is deliberately modest "
            "rather than highly precise."
        ),
        value_kind="zscore",
        related_features=(
            "shared_mythic_figure_count",
            "shared_figure_neighbor_zscore",
            "shared_mythic_figure_neighbor_count",
        ),
    ),
    PlaceSurvivalFeature(
        name="shared_figure_neighbor_zscore",
        title="Shared-Figure Neighbor Z-Score",
        category="Null-model comparisons",
        definition=(
            "How unusual the number of neighbours sharing figures with the focal "
            "place is relative to degree-preserving randomised place–figure "
            "networks."
        ),
        calculation=(
            "Use the same fixed-neighbour, degree-preserving place–figure rewirings "
            "as the shared-figure count null model, but compare the observed number "
            "of figure-sharing neighbours with its null mean and standard "
            "deviation. The current build uses 20 seeded samples."
        ),
        higher_value=(
            "More neighbours share figures with the place than expected under the "
            "null model."
        ),
        caution=(
            "A value of zero is also used when the sampled null distribution has "
            "zero variance; the estimate depends on the current graph and seed."
        ),
        value_kind="zscore",
        related_features=(
            "shared_mythic_figure_neighbor_count",
            "shared_figure_count_zscore",
            "shared_mythic_figure_count",
        ),
    ),
)


FEATURE_BY_NAME = {feature.name: feature for feature in FEATURE_CATALOG}
