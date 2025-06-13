import re, pandas as pd, streamlit as st

TARGET_COL = "Target gender (product.metafields.shopify.target-gender)"

GENERIC = {
    "TSHIRT","TSHIRTS","T-SHIRT","T-SHIRTS","SHIRT","SHIRTS",
    "HOODIE","HOODIES","SWEATSHIRT","SWEATSHIRTS","TROUSERS","PANTS",
    "SHORTS","JACKET","JACKETS","DRESS","DRESSES","SKIRT","SKIRTS",
    "UNDERWEAR","BELT","BELTS","SNEAKERS","SHOES","SLIDES","SANDALS",
    "SUNGLASSES","GLASSES","BAG","BAGS","TOTE","CLUTCH","POUCH",
    "KEYCHAIN","KEYCHAINS","SCARF","SCARVES","ASHRAY","ASHTRAY",
}

def extract_brand(title):
    words = title.split()
    brand = []
    for w in words:
        if w.replace("-", "").upper() in GENERIC: break
        brand.append(w)
    return (" ".join(brand) or words[0]).title()

def gender_from_group(g):
    gtags=set()
    if g["Option1 Name"].str.contains("MEN", case=False).any():
        gtags.add("Mens")
    elif g["Option1 Name"].str.contains("WOMEN", case=False).any():
        gtags.add("Womens")
    if not gtags.any():
        t = g["Title"].str.upper().str
        if t.contains(r"\bMENS?\b").any(): gtags.add("Mens")
        elif t.contains(r"\bWOMENS?\b").any(): gtags.add("Womens")
    if not gtags:
        nums=[int(m.group()) for v in g["Option1 Value"].fillna("").astype(str)
              if (m:=re.search(r"\d+", v))]
        if nums:
            if any(n>=40 for n in nums) and any(n<40 for n in nums):
                gtags.update(["Mens","Womens"])
            elif any(n>=40 for n in nums): gtags.add("Mens")
            else: gtags.add("Womens")
    return list(gtags)

def target_gender(tags):
    order=[("boys","BOYS"),("girls","GIRLS"),("mens","MENS"),("womens","WOMENS")]
    upper={t.strip().upper() for t in tags.split(",")}
    return "; ".join(l for l,u in order if u in upper)

def process(df):
    if TARGET_COL not in df.columns: df[TARGET_COL]=""
    df[["Title","Option1 Name"]] = (
        df.groupby("Handle")[["Title","Option1 Name"]].ffill()
    )

    for h,grp in df.groupby("Handle"):
        # tags
        tag_rows = grp["Tags"].fillna("").str.strip()!=""; 
        if tag_rows.any():
            tags=[t.strip() for t in grp.loc[tag_rows.idxmax(),"Tags"].split(",") if t.strip()]
            if "Lestyle" not in tags and "Outlet" not in tags: tags.append("Lestyle")
            if "Lestyle" in tags and "Outlet" in tags and (
                grp["Variant Compare At Price"].isna()|
                (grp["Variant Compare At Price"].astype(str).str.strip()=="")
            ).any(): tags=[t for t in tags if t!="Lestyle"]
            for gtag in gender_from_group(grp):
                if gtag not in tags: tags.append(gtag)
            df.loc[grp[tag_rows].index,"Tags"]=", ".join(tags)

        # vendor
        mask = grp["Vendor"].str.strip().str.lower()=="lestyle boutique"
        if mask.any():
            brand = extract_brand(grp["Title"].dropna().iloc[0])
            df.loc[grp[mask].index,"Vendor"]=brand

    # option1
    df.loc[df["Option1 Name"].fillna("").str.strip()!="","Option1 Name"]="SELECT SIZE"

    # target gender
    df[TARGET_COL]=df["Tags"].apply(lambda x: target_gender(x) if isinstance(x,str) else "")

    return df

st.title("CSV Tag & Vendor Cleaner")
uploaded = st.file_uploader("Upload CSV", type="csv")
if uploaded:
    df=pd.read_csv(uploaded)
    cleaned=process(df.copy())
    st.success("Processing complete!")
    st.download_button("Download cleaned CSV",
                       cleaned.to_csv(index=False).encode(),
                       file_name="products_modified.csv")
