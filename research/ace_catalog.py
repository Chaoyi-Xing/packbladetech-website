"""Reviewed ACE Converting & Packaging 2024 PDF rows with physical PDF page numbers.

Only entries that fit an approved PackBlade Tech category are included. The
supplier SKU is an ACE item number, never an OEM number. Shared diagram
observations are retained separately from item-row specifications.
"""

BS = "bag-making-sealing-knives"
SP = "serrated-packaging-knives"
FS = "film-cutting-slitting-knives"

ACE_ROWS = [
    dict(page=6, sku="458-10236001SS", category=BS, brand="Bosch", reference="8101804135", knife_type="Bagger knife", length="10.236 in", width="2.123 in", thickness="0.079 in", material="Stainless steel", coating="Uncoated", notes="PDF calls 8101804135 a model; its reference type requires review."),
    dict(page=6, sku="458-154979063", category=BS, brand="Bosch", model="SVE3800", knife_type="Bagger knife", length="15.492 in", width="0.791 in", thickness="0.063 in", material="Stainless steel", coating="Uncoated"),
    dict(page=9, sku="458-16519040", category=SP, brand="Cryovac", knife_type="Toothed packaging knife", length="16.535 in", width="1.968 in", thickness="0.040 in", material="Stainless steel", edge="toothed", coating="Uncoated"),
    dict(page=9, sku="458-01303032", category=FS, brand="Cryovac", knife_type="Piercing blade", length="1.33 in", width="0.39 in", thickness="0.032 in", material="Stainless steel", edge="piercing", coating="Uncoated", notes="PDF states bolt-on blade; exact machine model and film application are not listed."),
    dict(page=9, sku="458-1651904", category=BS, brand="Cryovac", reference="PV01S004", knife_type="Bagger knife", length="16.339 in", width="1.85 in", thickness="0.031 in", material="Stainless steel", coating="Uncoated"),
    dict(page=9, sku="458-01517032", category=FS, brand="Cryovac", knife_type="Two-point piercing blade", length="1.772 in", width="1.575 in", thickness="0.032 in", material="Stainless steel", edge="two-point piercing", holes="Two round mounting holes illustrated; sizes and spacing not stated", coating="Uncoated", notes="Dimensions transcribed from physical PDF page 9 diagram; film application and machine model require review."),
    dict(page=13, sku="458-H195000", category=BS, brand="Hayssen", reference="10137A0430", knife_type="Bagger knife", length="19.50 in", width="0.731 in", thickness="0.030 in", coating="Uncoated", notes="PDF calls 10137A0430 a model; Stiles lists it as a replacement part reference. Material is not stated."),
    dict(page=13, sku="458-H195000-TIN", category=BS, brand="Hayssen", reference="10137A0430", knife_type="Bagger knife", length="19.50 in", width="0.731 in", thickness="0.030 in", coating="TiN coated", notes="Coated variant of ACE 458-H195000; material is not stated."),
    dict(page=13, sku="458-H175000", category=BS, brand="Hayssen", reference="10137A0405", knife_type="Bagger knife", length="17.50 in", width="0.731 in", thickness="0.030 in", coating="TiN coated", notes="PDF calls 10137A0405 a model; Stiles lists it as a replacement part reference. Material is not stated."),
    dict(page=15, sku="458-23815039", category=SP, brand="Multivac", reference="79.912.7137.29", knife_type="Toothed knife", length="23.81 in / 605 mm", width="1.57 in / 40 mm", thickness="0.039 in / 1 mm", material="Stainless steel", edge="toothed", coating="Uncoated"),
    dict(page=15, sku="458-15915155", category=SP, brand="Multivac", reference="79.912.7128.00", knife_type="Zigzag toothed knife", length="15.9 in / 405 mm", width="1.57 in / 40 mm", thickness="0.155 in / 3.95 mm", material="Stainless steel", edge="zigzag toothed", coating="Uncoated"),
    dict(page=15, sku="458-15901039", category=SP, brand="Multivac", reference="79.912.7137.00", knife_type="Toothed knife", length="15.9 in / 405 mm", width="1.57 in / 40 mm", thickness="0.039 in / 1 mm", material="Stainless steel", edge="toothed", coating="Uncoated"),
]

# Page 11 dimensions and pictured slots belong to grouped illustrations, not
# individually identified rows. Store them as page observations, never as SKU facts.
for sku, teeth, angle, slot in [
    ("W-10027-60-TIN", 27, "60°", "No slots"),
    ("W-10027-60-TNS", 27, "60°", "0.040–0.042 in slot"),
    ("W-10027-75-TN", 27, "60°", "No slots"),
    ("W-10027-72-ST", 27, "60°", "0.030–0.032 in slot"),
    ("W-10040-42-TN", 40, "42°", "No slots"),
    ("W-1021204TN", 40, "42°", "0.030–0.032 in slot"),
    ("W-1021053-40TN", 40, None, "0.031 in slot"),
    ("W-10050-60TN", 50, "60°", "No slots"),
    ("W-10050-60-TNS", 50, "60°", "0.030–0.032 in slot"),
]:
    ACE_ROWS.append(dict(page=11, sku=sku, category=SP, brand="Gloucester", knife_type="Toothed packaging knife",
                         material="Carbon steel",
                         edge="toothed", tooth=f"{teeth} teeth" + (f", {angle} stated tooth angle" if angle else ""),
                         slot=slot, coating="TiN", notes="Item-row specification only. Page 11 grouped diagrams are not assigned to this SKU; verify dimensions against the installed knife."))

# Page 19 depicts OD/ID in shared Tidland class illustrations. Individual rows
# provide thickness, material and bevel wording, but not a confirmed substrate.
for sku, machine_class, shape, thickness, material, bevel, reference in [
    ("470-05931098D51", "Class II", "Dish slitter blade", "0.098 in", "52100", "compound single bevel", None),
    ("470-05900002", "Class II", "Dish shear slitter", "0.098 in", "D2", "compound single bevel", "128401"),
    ("470-05931098FD1", "Class II", "Flat slitter blade", "0.15 in", "D2", "compound single bevel", None),
    ("470-05931098DM1", "Class II", "Dish slitter blade", "0.098 in", "M2", "compound single bevel", None),
    ("470-05931098FM1", "Class II", "Flat slitter blade", "0.15 in", "M2", "compound single bevel", None),
    ("470-05931098FPS", "Class II", "Flat slitter blade", "0.15 in", "Powdered metal", "single bevel", None),
    ("470-07874002", "Class III", "Dish slitter blade", "0.157 in", "D2", "compound single bevel", "129833"),
    ("470-07931157FD1", "Class III", "Flat slitter blade", "0.197 in", "D2", "compound single bevel", None),
    ("470-07931157DM1", "Class III", "Dish slitter blade", "0.157 in", "M2", "compound single bevel", None),
    ("470-07931157FM1", "Class III", "Flat slitter blade", "0.197 in", "M2", "compound single bevel", None),
    ("470-07931157FPS", "Class III", "Flat slitter blade", "0.197 in", "Powdered metal", "single bevel", None),
    ("470-07931157FP1", "Class III", "Flat slitter blade", "0.197 in", "Powdered metal", "compound single bevel", "501835"),
]:
    ACE_ROWS.append(dict(page=19, sku=sku, category=FS, brand="Tidland", model=machine_class,
                         reference=reference, knife_type=shape, thickness=thickness, material=material,
                         edge=f"{shape.lower()}, {bevel}", coating="Uncoated",
                         notes="ACE catalog does not specify film substrate or an individual machine model. OD/ID appear only in shared class illustrations and are not assigned to this SKU."))

PAGE_OBSERVATIONS = [
    dict(observation_id="ACE-P11-GLOUCESTER-ILLUSTRATIONS", page=11,
         subject="Gloucester grouped illustrations",
         observation="Illustrations show 10.000 in length, 0.053 in thickness, widths of 2.125 in or 1.700 in, and elongated slots. The adjacent item rows have distinct slot descriptions, including four 'No slots' rows.",
         association="Ambiguous: illustrations are adjacent to groups of rows, not labelled with individual item numbers."),
    dict(observation_id="ACE-P19-TIDLAND-CLASS-II-ILLUSTRATION", page=19,
         subject="Tidland Class II illustration", observation="OD 5.906 in and ID 3.152 in are shown in a class illustration.",
         association="Class-level illustration; not confirmed for each listed SKU."),
    dict(observation_id="ACE-P19-TIDLAND-CLASS-III-ILLUSTRATION", page=19,
         subject="Tidland Class III illustration", observation="OD 7.874 in and ID 3.150 in are shown in a class illustration.",
         association="Class-level illustration; not confirmed for each listed SKU."),
]

assert len(ACE_ROWS) == 33
