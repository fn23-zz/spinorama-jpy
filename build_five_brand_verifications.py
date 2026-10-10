import json

OUT = "five_brand_verifications.json"
records = []

def add(speaker_id, model, *, each=None, pair=None, source_name, source_url, keyword, notes, confidence="high", availability="domestic_in_stock"):
    if pair is None and each is not None:
        pair = each * 2
    if pair is not None and each is None:
        each = round(pair / 2)
    records.append({
        "speaker_id": speaker_id, "price_jpy": pair, "price_each": each,
        "price_type": "pair", "availability": availability,
        "verification_status": "verified", "confidence_level": confidence,
        "source_name": source_name, "source_url": source_url,
        "search_keyword": keyword, "notes": notes,
    })

def unavailable(speaker_id, model, source_name, source_url, keyword, notes, confidence="high"):
    records.append({
        "speaker_id": speaker_id, "price_jpy": None, "price_each": None,
        "price_type": "pair", "availability": "not_available",
        "verification_status": "unavailable", "confidence_level": confidence,
        "source_name": source_name, "source_url": source_url,
        "search_keyword": keyword, "notes": notes,
    })

# Polk: price_jpy is always normalized to a stereo-pair equivalent.
polk_current = [
 (819,"Audio Reserve R100",None,62054,"https://kakaku.com/item/K0001361737/","Polk Audio Reserve R100 ブラウン ペア 新品","パッシブ・ペア販売の国内新品最安価格（税込）。"),
 (820,"Audio Reserve R200",None,81165,"https://kakaku.com/item/K0001361742/","Polk Audio Reserve R200 ホワイト ペア 新品","パッシブ・ペア販売の国内新品最安価格（税込）。"),
 (821,"Audio Reserve R350",44228,None,"https://kakaku.com/item/K0001361745/","Polk Audio Reserve R350 ブラウン 単品 新品","センター用パッシブ1本。price_jpyはステレオ比較用に2本換算。"),
 (822,"Audio Reserve R500",63000,None,"https://kakaku.com/item/K0001361750/","Polk Audio Reserve R500 ブラック 単品 新品","フロア型パッシブ1本。price_jpyはステレオ比較用に2本換算。"),
 (823,"Audio Reserve R700",106920,None,"https://kakaku.com/item/K0001361754/","Polk Audio Reserve R700 ブラック 単品 新品","フロア型パッシブ1本。price_jpyはステレオ比較用に2本換算。"),
 (825,"Audio Signature Elite ES20",None,46332,"https://kakaku.com/item/K0001378561/","Polk Audio Signature Elite ES20 ブラウン ペア 新品","パッシブ・ペア販売の国内新品最安価格（税込）。"),
 (826,"Audio Signature Elite ES60",66825,None,"https://kakaku.com/item/K0001381436/","Polk Audio Signature Elite ES60 ブラック 単品 新品","フロア型パッシブ1本。price_jpyはステレオ比較用に2本換算。"),
 (831,"Audio XT15",None,21060,"https://kakaku.com/item/K0001400375/","Polk Audio Monitor XT MXT15 ペア 新品","国内品番Monitor XT MXT15。パッシブ・ペア販売。"),
 (832,"Audio XT20",None,29043,"https://kakaku.com/item/K0001400376/","Polk Audio Monitor XT MXT20 ペア 新品","国内品番Monitor XT MXT20。パッシブ・ペア販売。"),
 (833,"Audio XT30",20241,None,"https://kakaku.com/item/K0001400377/","Polk Audio Monitor XT MXT30 単品 新品","国内品番Monitor XT MXT30。センター用1本、ペア換算で保存。"),
 (834,"Audio XT35",29520,None,"https://kakaku.com/item/K0001400378/","Polk Audio Monitor XT MXT35 単品 新品","国内品番Monitor XT MXT35。センター用1本、ペア換算で保存。"),
 (835,"Audio XT60",25282,None,"https://kakaku.com/item/K0001400379/","Polk Audio Monitor XT MXT60 単品 新品","国内品番Monitor XT MXT60。フロア型1本、ペア換算で保存。"),
 (836,"Audio XT70",37890,None,"https://kakaku.com/item/K0001400380/","Polk Audio Monitor XT MXT70 単品 新品","国内品番Monitor XT MXT70。フロア型1本、ペア換算で保存。"),
]
for i,m,e,p,u,k,n in polk_current: add(i,m,each=e,pair=p,source_name="価格.com",source_url=u,keyword=k,notes=n)
for i,m in [(813,"Audio 5JR"),(814,"Audio Atrium 4"),(815,"Audio Legend L200"),(816,"Audio Legend L800"),(817,"Audio Monitor 40 Series II"),(818,"Audio RT15i"),(824,"Audio Rti 10"),(827,"Audio Signature S15"),(828,"Audio Signature S30"),(829,"Audio T15"),(830,"Audio T50")]:
    unavailable(i,m,"Polk Japan（D&M Import Audio）","https://dm-importaudio.jp/polk/",f"Polk {m} 新品 国内","国内代理店の現行一覧と主要販売店で新品国内流通を確認できない旧製品。")

# Kali Audio: active monitor prices are per speaker unless explicitly a pair.
for i,m,e,u,k,n,c,a in [
 (585,"IN-5",49600,"https://www.hibino.com/view/page/kaliaudio","Kali Audio IN-5 価格 ヒビノ","国内正規品1本49,600円（税込）、2本換算。","medium","domestic_in_stock"),
 (587,"IN-8v2",59400,"https://www.hibino.com/view/page/kaliaudio","Kali Audio IN-8 V2 59,400円 ヒビノ","国内正規品1本59,400円（税込）、2本換算。","high","domestic_in_stock"),
 (589,"LP-6v2",25300,"https://www.hibino.com/view/page/kaliaudio-lpseries","Kali Audio LP-6 V2 25,300円 ヒビノ","国内正規品1本25,300円（税込）、2本換算。","high","domestic_in_stock"),
 (591,"LP-8v2",37180,"https://www.hibino.com/view/item/000000005891","Kali Audio LP-8 V2 37,180円 ヒビノ","国内正規品1本37,180円（税込）。取寄せ・納期確認商品。","high","domestic_in_stock")]:
    add(i,m,each=e,source_name="Hibino.com（国内正規代理店）",source_url=u,keyword=k,notes=n,confidence=c,availability=a)
add(592,"LP-UNF",pair=47850,source_name="Hibino.com（国内正規代理店）",source_url="https://www.hibino.com/view/item/000000006512",keyword="Kali Audio LP-UNF 価格 ヒビノ",notes="専用ケーブルで接続するステレオペア。国内正規店の税込47,850円（取寄せ）。")
for i,m in [(586,"IN-8"),(588,"LP-6"),(590,"LP-8"),(593,"SM-5")]:
    unavailable(i,m,"Hibino.com Kali Audio現行ラインナップ","https://www.hibino.com/view/page/kaliaudio",f"Kali Audio {m} 国内 新品","旧モデルまたは国内正規新品流通・現行価格を確認できない。")

# IK Multimedia iLoud.
add(400,"Multimedia iLoud MTM",each=52800,source_name="Yahoo!ショッピング（メリーネット）",source_url="https://shopping.yahoo.co.jp/search?p=IK%20Multimedia%20iLoud%20MTM",keyword="IK Multimedia iLoud MTM 1本 52,800円",notes="初代モデルの新品流通在庫。1本52,800円（税込）、比較用に2本換算。",confidence="medium")
add(401,"Multimedia iLoud MTM MKII",pair=154000,source_name="Hookup, Inc.（国内正規代理店）",source_url="https://hookup.co.jp/products/ik-multimedia/iloud-mtm-mkii/prices",keyword="iLoud MTM MKII Pair 国内正規品",notes="Pair（2本＋ARC MEMS測定用マイク）の国内正規価格154,000円（税込）。")
add(402,"Multimedia iLoud Micro Monitor",pair=66000,source_name="サウンドハウス",source_url="https://www.soundhouse.co.jp/products/detail/item/226155/",keyword="IK MULTIMEDIA iLoud Micro Monitor サウンドハウス",notes="左右ステレオペア。税込66,000円、特別注文。",availability="domestic_in_stock")

# Klipsch: normalize all single speakers to two-speaker equivalent in price_jpy.
for i,m,e,p,u,k,n in [
 (604,"Forte IV",660000,None,"https://kakaku.com/item/K0001715492/","Klipsch Forte IV 国内 新品 価格","パッシブ1本の国内新品最安価格。2本換算で保存。"),
 (605,"Heresy IV",429000,None,"https://kakaku.com/item/K0001259594/","Klipsch Heresy IV 国内 新品 価格","パッシブ1本の国内新品最安価格。2本換算で保存。"),
 (608,"RP-404C II",97548,None,"https://kakaku.com/item/K0001478528/","Klipsch RP-404C II 国内 新品 価格","センタースピーカー1本。比較用に2本換算。"),
 (610,"RP-500C II",64894,None,"https://kakaku.com/item/K0001478527/","Klipsch RP-500C II 国内 新品 価格","センタースピーカー1本。比較用に2本換算。"),
 (612,"RP-500M II",None,96264,"https://kakaku.com/item/K0001478518/","Klipsch RP-500M II 国内 新品 価格","パッシブ・ペア販売の国内新品最安価格。"),
 (613,"RP-504C II",105379,None,"https://kakaku.com/item/K0001478526/","Klipsch RP-504C II 国内 新品 価格","センタースピーカー1本。比較用に2本換算。"),
 (614,"RP-6000F II",123750,None,"https://kakaku.com/item/K0001478523/","Klipsch RP-6000F II 国内 新品 価格","フロア型1本。比較用に2本換算。"),
 (616,"RP-600M II",None,118196,"https://kakaku.com/item/K0001478519/","Klipsch RP-600M II 国内 新品 価格","パッシブ・ペア販売の国内新品最安価格。"),
 (617,"RP-8000F II",163350,None,"https://kakaku.com/item/K0001478522/","Klipsch RP-8000F II 国内 新品 価格","フロア型1本。比較用に2本換算。")]:
    add(i,m,each=e,pair=p,source_name="価格.com",source_url=u,keyword=k,notes=n)
for i,m in [(606,"Icon KF-26"),(607,"R41M"),(609,"RP-5000F II"),(611,"RP-500M"),(615,"RP-600M"),(618,"Synergy SB-3 Monitor"),(619,"The Fives"),(620,"The Nines"),(621,"The Three")]:
    unavailable(i,m,"価格.com","https://kakaku.com/search_results/Klipsch/",f"Klipsch {m} 国内 新品","旧製品または国内正規新品流通を確認できない。中古・並行輸入は採用しない。",confidence="medium" if i in (609,619,620) else "high")

# ADAM Audio: active monitors are sold individually.
for i,m,e,c in [(12,"A4V",71500,"high"),(14,"A7V",114400,"high"),(15,"S2V",199800,"medium"),(16,"T5V",28600,"high"),(17,"T7V",35900,"high"),(18,"T8V",42900,"high")]:
    add(i,m,each=e,source_name="Amazon.co.jp（国内正規品）",source_url=f"https://www.amazon.co.jp/s?k=ADAM+Audio+{m}",keyword=f"ADAM Audio {m}",notes=f"新品単品{e:,}円（税込）。アクティブモニターのため2本換算で保存。",confidence=c)
unavailable(13,"A5X","Amazon.co.jp","https://www.amazon.co.jp/s?k=ADAM+Audio+A5X","ADAM Audio A5X","旧製品。国内新品流通を確認できない。")

assert len(records)==61, len(records)
assert len({r['speaker_id'] for r in records})==61
json.dump(records,open(OUT,"w"),ensure_ascii=False,indent=2)
print(f"wrote {len(records)} records to {OUT}")
