# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""HSN and GST rates for the goods this group sells.

No Frappe import. Rates are the CBIC schedules in force from 22 September 2025
(Notification No. 9/2025-Central Tax (Rate) and Notification No. 10/2025-Central
Tax (Rate), both dated 17 September 2025). 8-digit codes follow the ITC (HS)
wording in the DGCI&S Chapter 9 tariff where that file states them. A row with
``ambiguous`` set is a code the tariff or the rate entry does not settle on its own.
"""

from __future__ import annotations

import re

# Notification No. 78/2020-Central Tax, 15 October 2020: above Rs 5 crore turnover
# in the preceding financial year, a tax invoice needs at least 6 digits.
MIN_HSN_DIGITS = 6

N9 = (
	"Notification No. 9/2025-Central Tax (Rate) dated 17 September 2025, "
	"Schedule I (5%), effective 22 September 2025"
)
N10 = (
	"Notification No. 10/2025-Central Tax (Rate) dated 17 September 2025 "
	"(nil / exempt), effective 22 September 2025"
)
TARIFF_CH9 = (
	"ITC (HS) Chapter 9, Directorate General of Commercial Intelligence and Statistics "
	"(https://www.dgciskol.gov.in/Writereaddata/Downloads/CHP_09.pdf)"
)
CHAPTER_NOTE = (
	"Customs Tariff Chapter 9 Note 1: a mixture of spices stays in Chapter 9 only while it "
	"keeps the essential character of those spices. Once salt or other ingredients make it a "
	"mixed condiment, it moves to heading 2103."
)

# kind: standard (one rate), packing (5% if pre-packaged and labelled, otherwise nil),
# nil, excluded (do not recommend; pan masala stayed out of the September 2025 food cut).
RATE_RULES = (
	{"code": "09092110", "rates": (0,), "kind": "nil", "label": "Coriander of seed quality", "source": N10},
	{"code": "09093111", "rates": (0,), "kind": "nil", "label": "Black cumin of seed quality", "source": N10},
	{"code": "09093121", "rates": (0,), "kind": "nil", "label": "Cumin of seed quality", "source": N10},
	{"code": "09101110", "rates": (0,), "kind": "nil", "label": "Fresh ginger, other than processed", "source": N10},
	{"code": "09103010", "rates": (0,), "kind": "nil", "label": "Fresh turmeric, other than processed", "source": N10},
	{"code": "11061010", "rates": (0,), "kind": "nil", "label": "Guar meal", "source": N10},
	{
		"code": "21069020",
		"rates": (),
		"kind": "excluded",
		"label": "Pan masala",
		"source": (
			"PIB release on the 56th GST Council meeting, 3 September 2025: pan masala stays on the "
			"pre-rationalisation rate until the compensation-cess borrowing is repaid. "
			"It is not in the 5% food list."
		),
	},
	{"code": "0904", "rates": (5,), "kind": "standard", "label": "Pepper and dried or ground chillies", "source": f"{N9}, entry 36"},
	{"code": "0905", "rates": (5,), "kind": "standard", "label": "Vanilla", "source": f"{N9}, entry 37"},
	{"code": "0906", "rates": (5,), "kind": "standard", "label": "Cinnamon and cinnamon-tree flowers", "source": f"{N9}, entry 38"},
	{"code": "0907", "rates": (5,), "kind": "standard", "label": "Cloves", "source": f"{N9}, entry 39"},
	{"code": "0908", "rates": (5,), "kind": "standard", "label": "Nutmeg, mace and cardamoms", "source": f"{N9}, entry 40"},
	{
		"code": "0909",
		"rates": (5,),
		"kind": "standard",
		"label": "Anise, fennel, coriander, cumin and caraway, other than seed quality",
		"source": f"{N9}, entry 41",
	},
	{
		"code": "0910",
		"rates": (5,),
		"kind": "standard",
		"label": "Ginger, saffron, turmeric, thyme, bay leaves, curry and other spices, other than fresh ginger and fresh turmeric",
		"source": f"{N9}, entry 42",
	},
	{
		"code": "1101",
		"rates": (5, 0),
		"kind": "packing",
		"label": "Wheat or meslin flour",
		"source": f"{N9}, entry 51; nil when not pre-packaged and labelled under {N10}",
	},
	{
		"code": "1102",
		"rates": (5, 0),
		"kind": "packing",
		"label": "Cereal flours other than wheat or meslin",
		"source": f"{N9}, entry 52; nil when not pre-packaged and labelled under {N10}",
	},
	{
		"code": "1106",
		"rates": (5, 0),
		"kind": "packing",
		"label": "Flour and powder of dried leguminous vegetables (besan, sattu), other than guar meal",
		"source": f"{N9}, entry 56; nil when not pre-packaged and labelled under {N10}",
	},
	{
		"code": "1208",
		"rates": (5,),
		"kind": "standard",
		"label": "Flour and meals of oil seeds, other than mustard",
		"source": f"{N9}, entry 68",
	},
	{
		"code": "1902",
		"rates": (5,),
		"kind": "standard",
		"label": "Pasta, noodles and seviyan (vermicelli)",
		"source": f"{N9}, entry 119. This was 12% before 22 September 2025.",
	},
	{
		"code": "2103",
		"rates": (5,),
		"kind": "standard",
		"label": "Sauces, mixed condiments and mixed seasonings",
		"source": f"{N9}, entry 139. This was 12% before 22 September 2025.",
	},
	{
		"code": "21061000",
		"rates": (5,),
		"kind": "standard",
		"label": "Texturised vegetable proteins (soya bari)",
		"source": f"{N9}, entry 142",
	},
	{
		"code": "2106",
		"rates": (5,),
		"kind": "standard",
		"label": "Food preparations not elsewhere specified, other than pan masala",
		"source": f"{N9}, entry 145, which excludes 21069020",
	},
	{
		"code": "3003",
		"rates": (5,),
		"kind": "standard",
		"label": "Medicaments not in measured doses, including Ayurvedic",
		"source": f"{N9}, entry 233. Some specified drugs are nil under {N10}.",
	},
	{
		"code": "3004",
		"rates": (5,),
		"kind": "standard",
		"label": "Retail medicaments, including Ayurvedic",
		"source": f"{N9}, entries 229 and 234. Some specified drugs are nil under {N10}.",
	},
)


def _cat(
	name,
	family,
	phrases,
	hsn,
	*,
	alternates=(),
	prefixes=(),
	reject=(),
	rates=(5,),
	ambiguous=False,
	note="",
	source,
	sort,
):
	return {
		"name": name,
		"family": family,
		"phrases": tuple(phrases),
		"hsn": hsn,
		"alternates": tuple(alternates),
		"prefixes": tuple(prefixes),
		"reject": tuple(reject),
		"rates": tuple(rates),
		"ambiguous": bool(ambiguous),
		"note": note,
		"source": source,
		"sort": sort,
	}


CATEGORIES = (
	_cat(
		"Black pepper, whole",
		"Whole Spice",
		("black pepper", "kali mirch", "kalimirch"),
		"09041130",
		alternates=("09041120", "09041140", "09041190"),
		prefixes=("090411",),
		reject=("09041110",),
		note=(
			"09041110 is long pepper, not black pepper. Garbled black pepper is 09041130, "
			"ungarbled is 09041140, and light black pepper is 09041120. All of heading 0904 is 5%."
		),
		source=f"{TARIFF_CH9}. {N9}, entry 36.",
		sort=10,
	),
	_cat(
		"Black pepper, ground",
		"Ground Spice",
		("black pepper powder", "black pepper ground", "pepper powder", "kali mirch powder"),
		"09041200",
		prefixes=("090412",),
		source=f"{TARIFF_CH9} (09041200 crushed or ground). {N9}, entry 36.",
		sort=20,
	),
	_cat(
		"Long pepper",
		"Whole Spice",
		("long pepper", "piper longum", "pippali"),
		"09041110",
		source=f"{TARIFF_CH9} (09041110 pepper, long). {N9}, entry 36.",
		sort=30,
	),
	_cat(
		"Chilli, whole dried",
		"Whole Spice",
		("chilli whole", "chili whole", "dried chilli", "dried chili", "red chilli", "red chili", "lal mirch"),
		"09042110",
		prefixes=("090421",),
		note="09042110 is dried fruits of genus Capsicum, neither crushed nor ground. Heading 0904 is 5%.",
		source=f"{TARIFF_CH9}. {N9}, entry 36.",
		sort=40,
	),
	_cat(
		"Chilli, crushed or powder",
		"Ground Spice",
		("chilli powder", "chili powder", "chilly powder", "chilli crushed", "red chilli powder", "lal mirch powder"),
		"09042211",
		alternates=("09042219",),
		prefixes=("090422",),
		note="09042211 is chilli powder. Other crushed capsicum is 09042219. Chilli seeds are 09042212.",
		source=f"{TARIFF_CH9}. {N9}, entry 36.",
		sort=50,
	),
	_cat(
		"Coriander, whole",
		"Whole Spice",
		("coriander whole", "coriander", "sabut dhania", "dhania"),
		"09092190",
		prefixes=("090921",),
		reject=("09092110",),
		note="Food coriander that is not of seed quality is 09092190 at 5%. Seed quality (09092110) is nil.",
		source=f"{TARIFF_CH9}. {N9}, entry 41. Seed quality: {N10}.",
		sort=60,
	),
	_cat(
		"Coriander, ground",
		"Ground Spice",
		("coriander powder", "dhania powder", "ground coriander"),
		"09092200",
		prefixes=("090922",),
		source=f"{TARIFF_CH9} (09092200 crushed or ground). {N9}, entry 41.",
		sort=70,
	),
	_cat(
		"Cumin (jeera), whole",
		"Whole Spice",
		("cumin", "jeera", "zeera", "jira"),
		"09093129",
		alternates=("09093119",),
		prefixes=("090931",),
		reject=("09093111", "09093121"),
		note=(
			"09093129 is cumin, other than black, not of seed quality. Black cumin that is not seed "
			"quality is 09093119. Seed quality (09093121 and 09093111) is nil, not the 5% spice rate."
		),
		source=f"{TARIFF_CH9}. {N9}, entry 41. Seed quality: {N10}.",
		sort=80,
	),
	_cat(
		"Cumin (jeera), ground",
		"Ground Spice",
		("cumin powder", "jeera powder", "ground cumin"),
		"09093200",
		prefixes=("090932",),
		source=f"{TARIFF_CH9} (09093200 crushed or ground). {N9}, entry 41.",
		sort=90,
	),
	_cat(
		"Fennel (saunf), whole",
		"Whole Spice",
		("fennel", "saunf", "sauf"),
		"090961",
		ambiguous=True,
		note=(
			"Sub-heading 090961 covers anise, badian, caraway and fennel, neither crushed nor ground. "
			"Six digits meet the invoice rule. The 8-digit item for fennel that is not seed quality "
			"has to be read off the current ITC (HS); seed quality of heading 0909 is nil."
		),
		source=f"{N9}, entry 41. Seed quality nil: {N10}. Tariff heading 0909.",
		sort=100,
	),
	_cat(
		"Fennel (saunf), ground",
		"Ground Spice",
		("fennel powder", "saunf powder"),
		"090962",
		ambiguous=True,
		note=(
			"Sub-heading 090962 is anise, badian, caraway or fennel, crushed or ground. "
			"Confirm the final two digits in the current tariff before printing an 8-digit code. The rate is 5%."
		),
		source=f"{N9}, entry 41.",
		sort=110,
	),
	_cat(
		"Turmeric, dried",
		"Whole Spice",
		("turmeric", "haldi"),
		"09103020",
		prefixes=("09103020",),
		reject=("09103010",),
		note="Dried turmeric is 09103020 at 5%. Fresh turmeric (09103010) is nil. Powder is 09103030.",
		source=f"{TARIFF_CH9}. {N9}, entry 42. Fresh: {N10}.",
		sort=120,
	),
	_cat(
		"Turmeric, powder",
		"Ground Spice",
		("turmeric powder", "haldi powder"),
		"09103030",
		source=f"{TARIFF_CH9} (09103030 powder). {N9}, entry 42.",
		sort=130,
	),
	_cat(
		"Turmeric, fresh",
		"Whole Spice",
		("fresh turmeric",),
		"09103010",
		rates=(0,),
		note="Fresh turmeric, other than in processed form, is nil-rated.",
		source=f"{TARIFF_CH9}. {N10}.",
		sort=140,
	),
	_cat(
		"Ginger, dried",
		"Whole Spice",
		("dry ginger", "dried ginger", "sonth", "saunth"),
		"09101120",
		alternates=("09101130",),
		note="Unbleached dried ginger is 09101120. Bleached dried ginger is 09101130. Fresh ginger is 09101110 and is nil.",
		source=f"{TARIFF_CH9}. {N9}, entry 42.",
		sort=150,
	),
	_cat(
		"Ginger, powder",
		"Ground Spice",
		("ginger powder", "sonth powder"),
		"09101210",
		alternates=("09101290",),
		note="09101210 is ginger powder. Other crushed ginger is 09101290.",
		source=f"{TARIFF_CH9}. {N9}, entry 42.",
		sort=160,
	),
	_cat(
		"Ginger, fresh",
		"Whole Spice",
		("fresh ginger", "adrak"),
		"09101110",
		rates=(0,),
		note="Fresh ginger, other than in processed form, is nil-rated.",
		source=f"{TARIFF_CH9}. {N10}.",
		sort=170,
	),
	_cat(
		"Cardamom, whole",
		"Whole Spice",
		("cardamom", "elaichi", "elachi"),
		"090831",
		ambiguous=True,
		note=(
			"Sub-heading 090831 is cardamom, neither crushed nor ground. Large, small and bleached "
			"cardamom have different 8-digit items. The GST rate for heading 0908 is 5% either way."
		),
		source=f"{N9}, entry 40.",
		sort=180,
	),
	_cat(
		"Cardamom, ground",
		"Ground Spice",
		("cardamom powder", "elaichi powder"),
		"090832",
		ambiguous=True,
		note="Sub-heading 090832 is cardamom, crushed or ground. Confirm the 8-digit item in the current tariff. The rate is 5%.",
		source=f"{N9}, entry 40.",
		sort=190,
	),
	_cat(
		"Cloves, whole",
		"Whole Spice",
		("clove", "cloves", "laung"),
		"09071020",
		alternates=("09071010",),
		note="09071020 is cloves not extracted. 09071010 is extracted cloves. Heading 0907 is 5%.",
		source=f"{N9}, entry 39. ITC (HS) 0907.",
		sort=200,
	),
	_cat(
		"Cloves, ground",
		"Ground Spice",
		("clove powder", "cloves powder", "ground clove"),
		"09072000",
		source=f"{N9}, entry 39. ITC (HS) 09072000 crushed or ground.",
		sort=210,
	),
	_cat(
		"Cinnamon, whole",
		"Whole Spice",
		("cinnamon", "dalchini", "dal chini"),
		"090611",
		ambiguous=True,
		note="Quills, chips and cassia split the 8-digit items under heading 0906. Six digits are enough for the invoice rule. The rate is 5%.",
		source=f"{N9}, entry 38.",
		sort=220,
	),
	_cat(
		"Cinnamon, ground",
		"Ground Spice",
		("cinnamon powder", "dalchini powder"),
		"090620",
		ambiguous=True,
		note="Sub-heading 090620 is cinnamon, crushed or ground. Confirm the 8-digit item before printing one. The rate is 5%.",
		source=f"{N9}, entry 38.",
		sort=230,
	),
	_cat(
		"Fenugreek (methi)",
		"Whole Spice",
		("fenugreek", "methi"),
		"091099",
		ambiguous=True,
		note=(
			"Fenugreek sits in 091099 (other spices). The 8-digit item has to come from the current "
			"ITC (HS). Heading 0910, other than fresh ginger and fresh turmeric, is 5%."
		),
		source=f"{N9}, entry 42.",
		sort=240,
	),
	_cat(
		"Ajwain",
		"Whole Spice",
		("ajwain", "carom"),
		"091099",
		ambiguous=True,
		note="Ajwain is under 091099 (other spices). Confirm the 8-digit item in the current tariff. The rate for this heading is 5%.",
		source=f"{N9}, entry 42.",
		sort=250,
	),
	_cat(
		"Spice mixture (spices only)",
		"Masala",
		("spice mixture", "mixed spices", "spice mix"),
		"09109100",
		alternates=("21039040",),
		prefixes=("091091",),
		ambiguous=True,
		note=(
			"09109100 is mixtures of spices referred to in Chapter 9 Note 1(b). "
			"If the blend contains salt or other condiments it is a mixed seasoning under 21039040. Both are 5%."
		),
		source=f"{TARIFF_CH9} (09109100). {CHAPTER_NOTE} {N9}, entries 42 and 139.",
		sort=260,
	),
	_cat(
		"Mixed masala and seasoning",
		"Masala",
		("garam masala", "kitchen king", "curry powder", "mixed masala", "masala blend", "seasoning"),
		"21039040",
		alternates=("09109100",),
		prefixes=("21039040", "091091"),
		ambiguous=True,
		rates=(5,),
		note=(
			"21039040 is mixed condiments and mixed seasonings. A blend that is only spices, with no salt "
			"or other ingredients, can stay at 09109100. Both are 5% from 22 September 2025. "
			"This row is ambiguous on purpose."
		),
		source=f"{CHAPTER_NOTE} {N9}, entry 139 (2103) and entry 42 (0910).",
		sort=270,
	),
	_cat(
		"Sauces and condiments",
		"Seasoning",
		("sauce", "sauces", "ketchup", "chutney", "mayonnaise", "salad dressing", "curry paste"),
		"21039090",
		alternates=("21031000", "21032000", "21039010", "21039020", "21039030", "21039040"),
		prefixes=("2103",),
		ambiguous=True,
		note=(
			"Every good of heading 2103 is 5% from 22 September 2025 (it was 12% before that). "
			"Soya sauce is 21031000, tomato ketchup is 21032000, curry paste is 21039010, "
			"chilli sauce is 21039020, mayonnaise is 21039030, mixed seasonings are 21039040, "
			"and other sauces are 21039090."
		),
		source=f"{N9}, entry 139.",
		sort=280,
	),
	_cat(
		"Pasta and noodles",
		"Pasta",
		("pasta", "macaroni", "spaghetti", "penne", "noodle", "noodles"),
		"19021900",
		alternates=("19021100", "19023010"),
		prefixes=("1902",),
		ambiguous=True,
		note=(
			"Heading 1902, including cooked, stuffed and instant pasta, is 5% from 22 September 2025. "
			"19021900 is uncooked pasta without eggs. Pasta with eggs is 19021100. "
			"Instant noodles are often 19023010. The rate does not change between those items."
		),
		source=f"{N9}, entry 119.",
		sort=290,
	),
	_cat(
		"Vermicelli (seviyan)",
		"Vermicelli",
		("vermicelli", "seviyan", "seviya", "semiya", "sewai"),
		"19021900",
		alternates=("19023010",),
		prefixes=("1902",),
		ambiguous=True,
		note=(
			"The 5% entry names seviyan (vermicelli) under heading 1902. Uncooked seviyan is usually "
			"19021900. Fried or instant vermicelli may be 19023010. Either way the rate is 5%."
		),
		source=f"{N9}, entry 119.",
		sort=300,
	),
	_cat(
		"Soya chunks (soya bari)",
		"Soya",
		("soya chunks", "soya chunk", "soy chunks", "soya bari", "soya nuggets", "soy nuggets", "textured soya", "textured soy", "soya"),
		"21061000",
		note=(
			"Notification entry 142 names texturised vegetable proteins (soya bari) under 2106 at 5%. "
			"Soya flour is a different product: 12081000, also 5%, under entry 68. "
			"A name that only says soya matches both rows; the audit will not pick one."
		),
		source=f"{N9}, entry 142. ITC (HS) 21061000 protein concentrates and textured protein substances.",
		sort=310,
	),
	_cat(
		"Soya flour",
		"Soya",
		("soya flour", "soy flour", "soya meal", "soyabean flour", "soybean flour", "soya"),
		"12081000",
		prefixes=("120810",),
		note="Flour and meals of soya beans are 12081000 at 5%. This is not soya chunks (21061000).",
		source=f"{N9}, entry 68 (flour and meals of oil seeds, other than mustard).",
		sort=320,
	),
	_cat(
		"Besan (gram flour)",
		"Staple",
		("besan", "gram flour", "chana flour", "chickpea flour"),
		"11061090",
		prefixes=("11061090",),
		reject=("11061010",),
		rates=(5, 0),
		ambiguous=True,
		note=(
			"Besan of chana is 11061090 (other), not guar meal 11061010, which is nil-rated and is the wrong code. "
			"Pre-packaged and labelled besan is 5%. Besan that is not pre-packaged and labelled is nil. "
			"A branded SK Gourmet pack is the 5% case. The audit does not change the tax template on its own, "
			"because a loose pack and a labelled pack are both lawful."
		),
		source=f"{N9}, entry 56. Nil when not pre-packaged and labelled, and guar meal 11061010, under {N10}.",
		sort=330,
	),
	_cat(
		"Sattu",
		"Staple",
		("sattu",),
		"11061090",
		prefixes=("1106", "1102"),
		reject=("11061010",),
		rates=(5, 0),
		ambiguous=True,
		note=(
			"Roasted chana sattu is flour of a dried leguminous vegetable, so 11061090, with the same "
			"pre-packaged 5% / loose nil split as besan. Sattu made from a cereal such as barley is heading 1102, "
			"again 5% if pre-packaged and labelled and nil otherwise. It is not automatically heading 2106. "
			"Confirm the grain on the pack."
		),
		source=f"{N9}, entries 56 (1106) and 52 (1102). Nil when not pre-packaged and labelled under {N10}.",
		sort=340,
	),
	_cat(
		"Wheat flour (atta, maida)",
		"Staple",
		("atta", "maida", "wheat flour", "refined flour"),
		"11010000",
		prefixes=("1101",),
		rates=(5, 0),
		ambiguous=True,
		note="Heading 1101. Pre-packaged and labelled wheat flour is 5%. Flour that is not pre-packaged and labelled is nil.",
		source=f"{N9}, entry 51. Nil when not pre-packaged and labelled under {N10}.",
		sort=350,
	),
	_cat(
		"Sunkeera and other wellness",
		"Wellness",
		("sunkeera", "wellness", "nutraceutical", "food supplement", "ayurvedic"),
		"300490",
		alternates=("21069099",),
		prefixes=("3004", "2106"),
		reject=("21069020",),
		ambiguous=True,
		note=(
			"The product licence decides the heading. A retail Ayurvedic medicament is heading 3004 at 5%, "
			"unless that formulation is in the nil list of Notification 10/2025. A food preparation that is "
			"not a medicament is heading 2106, other than pan masala 21069020, also at 5%. "
			"Do not use 21069020. The 8-digit item under 3004 has to match the licence."
		),
		source=f"{N9}, entries 229, 234 and 145.",
		sort=360,
	),
)

_PHRASE_SPLIT = re.compile(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])")


def clean_hsn(value) -> str:
	return re.sub(r"\D", "", str(value or ""))


def hsn_has_letters(value) -> bool:
	return bool(re.search(r"[A-Za-z]", str(value or "")))


def _normalise_text(*parts) -> str:
	raw = " ".join(str(part or "") for part in parts).lower()
	raw = raw.replace("-", " ").replace("_", " ").replace("/", " ")
	raw = _PHRASE_SPLIT.sub(" ", raw)
	return " ".join(raw.split())


def _phrase_in(phrase, text) -> bool:
	return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def match_categories(item_name="", item_code="", item_group="") -> list[dict]:
	"""Best name matches. A longer phrase wins, so 'jeera powder' is not also whole jeera."""
	text = _normalise_text(item_name, item_code, item_group)
	if not text:
		return []
	scored = []
	for category in CATEGORIES:
		score = 0
		for phrase in category["phrases"]:
			if _phrase_in(phrase, text):
				score = max(score, len(phrase))
		if score:
			scored.append((score, category["sort"], category))
	if not scored:
		return []
	best = max(row[0] for row in scored)
	return [row[2] for row in scored if row[0] == best]


def find_rate_rule(hsn) -> dict | None:
	digits = clean_hsn(hsn)
	if len(digits) < 4:
		return None
	found = None
	for rule in RATE_RULES:
		if digits.startswith(rule["code"]) and (found is None or len(rule["code"]) > len(found["code"])):
			found = rule
	return found


def rate_conflict(hsn) -> bool:
	"""True when a 4- or 6-digit code covers child items that are not all the same rate."""
	digits = clean_hsn(hsn)
	if len(digits) < 4 or len(digits) >= 8:
		return False
	matched = find_rate_rule(digits)
	if not matched:
		return False
	own = tuple(matched["rates"])
	for rule in RATE_RULES:
		if rule["code"].startswith(digits) and len(rule["code"]) > len(digits) and tuple(rule["rates"]) != own:
			return True
	return False


def _codes(category) -> list[str]:
	values = [category["hsn"], *category["alternates"]]
	return [clean_hsn(value) for value in values if clean_hsn(value)]


def hsn_fits(category, hsn) -> bool:
	digits = clean_hsn(hsn)
	if not digits:
		return False
	for rejected in category["reject"]:
		code = clean_hsn(rejected)
		if code and (digits == code or digits.startswith(code)):
			return False
	for code in _codes(category):
		if digits == code or digits.startswith(code) or (code.startswith(digits) and len(digits) >= MIN_HSN_DIGITS):
			return True
	for prefix in category["prefixes"]:
		code = clean_hsn(prefix)
		if code and digits.startswith(code):
			return True
	return False


def hsn_in_master(hsn, known) -> bool | None:
	"""None when the GST HSN master was not available. True when this code or a parent is present."""
	if known is None:
		return None
	digits = clean_hsn(hsn)
	if not digits or not known:
		return None
	if digits in known:
		return True
	for code in known:
		if len(code) >= 4 and (digits.startswith(code) or code.startswith(digits)):
			return True
	return False


def rates_label(rates) -> str:
	shown = [str(int(rate)) if float(rate).is_integer() else str(rate) for rate in rates]
	if not shown:
		return "a rate this table does not recommend"
	if len(shown) == 1:
		return f"GST {shown[0]}%"
	return " or ".join(f"GST {rate}%" for rate in shown)


def fixture_records() -> list[dict]:
	"""Rows for the HSN Category Map DocType. This does not describe any Item."""
	rows = []
	for category in CATEGORIES:
		rates = category["rates"]
		rows.append(
			{
				"doctype": "HSN Category Map",
				"name": category["name"],
				"category_name": category["name"],
				"product_family": category["family"],
				"phrases": "\n".join(category["phrases"]),
				"hsn_code": category["hsn"],
				"alternate_hsn": ", ".join(category["alternates"]),
				"accept_prefix": ", ".join(category["prefixes"]),
				"reject_hsn": ", ".join(category["reject"]),
				"gst_rate": rates[0] if rates else 0,
				"allowed_rates": ", ".join(str(int(rate) if float(rate).is_integer() else rate) for rate in rates),
				"ambiguous": 1 if category["ambiguous"] else 0,
				"ambiguity_note": category["note"],
				"source": category["source"],
				"effective_from": "2025-09-22",
				"sort_order": category["sort"],
			}
		)
	return rows
