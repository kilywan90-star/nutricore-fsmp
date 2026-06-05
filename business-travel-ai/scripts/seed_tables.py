#!/usr/bin/env python3
# Quick seed: hotels, transport, attractions, shopping
import sqlite3, os

DB = 'E:/claude/business-travel-ai/data/travel.db'
db = sqlite3.connect(DB)

# === Hotels ===
db.executescript("""
CREATE TABLE IF NOT EXISTS hotels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, city TEXT NOT NULL, district TEXT, address TEXT NOT NULL,
    star_level INTEGER DEFAULT 4, hotel_type TEXT DEFAULT 'business',
    price_min INTEGER, price_max INTEGER, rating REAL DEFAULT 4.0,
    privacy_level TEXT DEFAULT 'L2', meeting_rooms INTEGER DEFAULT 0,
    max_capacity INTEGER, scene_tags TEXT DEFAULT '[]',
    highlights TEXT DEFAULT '[]', contact_phone TEXT,
    opening_hours TEXT DEFAULT '24h', reserve_note TEXT,
    data_source TEXT DEFAULT 'seed',
    created_at TEXT DEFAULT (datetime('now','localtime'))
)
""")

hotels = [
    ("成都博舍酒店","成都","锦江区","笔帖式街81号",5,"boutique",1200,2800,4.8,"L4",3,120,"高端私密商务","太古里内,谧寻SPA,井酒吧","028-66369999","24小时","提前5天"),
    ("成都世纪城天堂洲际","成都","高新区","世纪城路88号",5,"business",600,1500,4.5,"L3",10,500,"大型会议,会展","万人宴会厅,大堂茶廊","028-85348888","24小时",None),
    ("成都协信中心希尔顿","成都","成华区","建设路协信中心",4,"business",400,900,4.3,"L2",3,100,"商务出差","希尔顿荣誉客会,全日餐厅","028-65559888","24小时",None),
    ("成都西藏饭店","成都","金牛区","人民北路一段10号",4,"business",350,800,4.2,"L2",3,150,"商务出差,政务","藏式建筑,藏餐厅","028-83183388","24小时",None),
    ("北京国贸大酒店","北京","朝阳区","建国门外大街1号",5,"luxury",1800,5000,4.9,"L4",12,500,"顶级商务","天际泳池,米其林,行政酒廊","010-65052288","24小时","提前3天"),
    ("北京王府半岛","北京","东城区","王府井金鱼胡同8号",5,"luxury",1500,3500,4.8,"L4",8,300,"高端商务","半岛水疗,法式下午茶","010-85162888","24小时","提前2天"),
    ("北京金融街丽思卡尔顿","北京","西城区","金融街金城坊东街1号",5,"luxury",1600,4000,4.8,"L4",10,400,"金融商务","行政会议室,恒温泳池","010-66016666","24小时",None),
    ("上海浦东丽思卡尔顿","上海","浦东新区","世纪大道8号",5,"luxury",2000,6000,4.9,"L4",10,400,"顶级商务","黄浦江景,米其林二星","021-20201188","24小时","提前7天"),
    ("上海外滩华尔道夫","上海","黄浦区","中山东一路2号",5,"luxury",1800,5000,4.9,"L4",6,300,"高端外事","江景长廊,下午茶,管家服务","021-63229988","24小时","提前3天"),
    ("上海静安香格里拉","上海","静安区","延安中路1218号",5,"business",1200,2800,4.7,"L3",8,350,"商务会议","大型宴会厅,CHI水疗","021-22038888","24小时",None),
    ("深圳瑞吉酒店","深圳","罗湖区","深南东路5016号",5,"luxury",1500,3800,4.8,"L4",8,350,"顶级商务","云端大堂,高空泳池","0755-83088888","24小时","提前3天"),
    ("深圳福田香格里拉","深圳","福田区","益田路4088号",5,"business",900,2200,4.6,"L3",7,280,"商务会议","户外泳池,豪华宴会厅","0755-88284088","24小时",None),
    ("广州四季酒店","广州","天河区","珠江新城珠江西路5号",5,"luxury",1400,3500,4.8,"L4",8,300,"顶级商务","IFC70-100层,云端大堂","020-88833888","24小时","提前3天"),
    ("杭州西子湖四季","杭州","西湖区","灵隐路5号",5,"luxury",1800,5000,4.9,"L4",3,150,"顶级私密商务","园林式酒店,金沙厅","0571-88298888","24小时","提前7天"),
    ("杭州柏悦酒店","杭州","上城区","钱江路1366号",5,"luxury",1200,3000,4.8,"L4",5,200,"高端商务","钱塘江景,空中大堂","0571-86969999","24小时",None),
    ("重庆解放碑威斯汀","重庆","渝中区","新华路222号",5,"luxury",800,2000,4.7,"L3",5,200,"商务接待","高空泳池,江景套房","023-63806666","24小时",None),
    ("武汉万达瑞华","武汉","武昌区","东湖路138号",5,"luxury",800,2000,4.7,"L4",6,300,"高端商务","东湖景观,艺术收藏","027-59599999","24小时",None),
    ("西安丽思卡尔顿","西安","高新区","科技路38号",5,"luxury",1000,2500,4.7,"L4",6,280,"高端商务","行政酒廊,Flair酒吧","029-88815888","24小时",None),
    ("南京丽思卡尔顿","南京","玄武区","中山路18号",5,"luxury",1000,2500,4.7,"L4",5,250,"高端商务","新街口天际线","025-86858888","24小时",None),
    ("长沙尼依格罗","长沙","天心区","解放西路188号",5,"luxury",700,1800,4.6,"L3",4,180,"商务接待","IFS云端大堂,高空酒吧","0731-82958888","24小时",None),
    ("昆明洲际酒店","昆明","西山区","怡景路5号",5,"luxury",600,1500,4.6,"L3",5,250,"商务会议","滇池景观,花园泳池","0871-63188888","24小时",None),
]
for h in hotels:
    db.execute("INSERT INTO hotels (name,city,district,address,star_level,hotel_type,price_min,price_max,rating,privacy_level,meeting_rooms,max_capacity,scene_tags,highlights,contact_phone,opening_hours,reserve_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", h)
print(f"Hotels: {len(hotels)}")

# === Transport ===
cnt = db.execute("SELECT count(*) FROM transport_routes").fetchone()[0]
if cnt == 0:
    routes = [
        ("flight","北京","上海","北京首都T3","上海虹桥T2","中国国航","CA1501","08:00","10:15",135,1280,3800,"空客A350",1,"WiFi,餐食"),
        ("flight","北京","上海","北京首都T3","上海虹桥T2","中国国航","CA1521","14:00","16:10",130,1050,3200,"空客A320",1,"餐食"),
        ("flight","北京","深圳","北京首都T3","深圳宝安T3","中国国航","CA1301","07:30","10:45",195,1500,4500,"空客A330",1,"WiFi,餐食"),
        ("flight","上海","深圳","上海虹桥T2","深圳宝安T3","东方航空","MU5331","08:00","10:30",150,1380,3800,"空客A330",1,"WiFi,餐食"),
        ("flight","北京","广州","北京首都T3","广州白云T2","中国国航","CA1301","08:00","11:10",190,1680,4800,"波音787",1,"WiFi,餐食"),
        ("flight","北京","成都","北京首都T3","成都天府T1","中国国航","CA4101","08:30","11:30",180,1480,4200,"空客A330",1,"餐食"),
        ("flight","上海","成都","上海虹桥T2","成都天府T1","东方航空","MU5401","09:00","12:00",180,1480,4000,"空客A330",1,"餐食"),
        ("flight","深圳","成都","深圳宝安T3","成都双流T1","深圳航空","ZH9401","09:00","11:30",150,1380,3800,"空客A330",1,"WiFi,餐食"),
        ("flight","北京","杭州","北京首都T3","杭州萧山T3","中国国航","CA1701","08:30","10:45",135,1200,3500,"空客A320",1,"餐食"),
        ("train","北京","上海","北京南","上海虹桥","中国铁路","G1","07:00","11:29",269,553,1748,"复兴号CR400",1,"WiFi,餐车,商务座"),
        ("train","北京","上海","北京南","上海虹桥","中国铁路","G7","11:00","15:25",265,553,1748,"复兴号CR400",1,"WiFi,餐车"),
        ("train","上海","杭州","上海虹桥","杭州东","中国铁路","G7301","07:00","07:52",52,73,219,"复兴号CR400",1,"WiFi,电源插座"),
        ("train","上海","南京","上海虹桥","南京南","中国铁路","G7001","07:00","08:02",62,82,260,"复兴号CR400",1,"WiFi,电源插座"),
        ("train","广州","深圳","广州南","深圳北","中国铁路","C7001","07:00","07:37",37,74,150,"复兴号CR400",1,"WiFi"),
        ("train","成都","重庆","成都东","重庆北","中国铁路","G8501","07:30","08:50",80,96,280,"复兴号CR400",1,"WiFi"),
        ("train","北京","西安","北京西","西安北","中国铁路","G651","07:00","11:30",270,450,1350,"复兴号CR400",1,"WiFi,餐车,商务座"),
        ("flight","上海","重庆","上海浦东T1","重庆江北T2","东方航空","MU5421","10:00","13:00",180,1380,3800,"波音737",1,"餐食"),
        ("flight","北京","重庆","北京首都T3","重庆江北T2","中国国航","CA4131","08:00","11:00",180,1480,4200,"空客A330",1,"餐食"),
    ]
    for r in routes:
        db.execute("INSERT INTO transport_routes (transport_type,origin_city,dest_city,origin_station,dest_station,carrier_name,route_number,departure_time,arrival_time,duration_minutes,price_economy,price_business,vehicle_type,schedule_days,amenities,data_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r)
    print(f"Transport: {len(routes)}")
else:
    print(f"Transport: {cnt} (skip)")

# === Attractions ===
db.executescript("""
CREATE TABLE IF NOT EXISTS attractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, city TEXT NOT NULL, district TEXT, address TEXT NOT NULL,
    category TEXT DEFAULT '景点', price_min INTEGER, price_max INTEGER,
    rating REAL DEFAULT 4.0, duration_min INTEGER DEFAULT 120,
    scene_tags TEXT DEFAULT '[]', description TEXT, highlights TEXT DEFAULT '[]',
    contact_phone TEXT, opening_hours TEXT DEFAULT '09:00-17:00',
    reserve_note TEXT, tips TEXT, data_source TEXT DEFAULT 'seed',
    created_at TEXT DEFAULT (datetime('now','localtime'))
)
""")
cnt = db.execute("SELECT count(*) FROM attractions").fetchone()[0]
if cnt == 0:
    attractions = [
        ("故宫博物院","北京","东城区","景山前街4号","历史古迹",40,60,4.9,240,"商务文化","世界最大宫殿群","太和殿,珍宝馆","010-85007421","08:30-17:00","提前7天","上午9点前入场"),
        ("八达岭长城","北京","延庆区","八达岭镇","历史古迹",35,45,4.8,240,"团队活动","世界新七大奇迹","好汉坡,北八楼","010-69121383","07:30-18:00",None,"上午8点前到"),
        ("外滩","上海","黄浦区","中山东一路","城市景观",0,0,4.9,60,"商务散步","万国建筑博览","黄浦江夜景",None,"全天",None,"夜晚最佳"),
        ("东方明珠","上海","浦东新区","世纪大道1号","现代建筑",100,220,4.5,90,"商务观光","上海地标","太空舱,旋转餐厅","021-58791888","08:00-21:30",None,"傍晚登塔"),
        ("深圳湾公园","深圳","南山区","滨海大道","自然景观",0,0,4.7,120,"商务散步","最美海滨长廊","日出剧场,红树林",None,"全天",None,"晨跑傍晚散步"),
        ("广州塔","广州","天河区","阅江西路222号","现代建筑",150,398,4.6,120,"商务观光","广州地标","488米观景台","020-89338222","09:30-22:30",None,"傍晚看日落"),
        ("大熊猫繁育基地","成都","成华区","熊猫大道1375号","自然景观",55,58,4.8,180,"商务观光,客户招待","世界最大熊猫保护机构","幼年熊猫,熊猫产房","028-83510033","07:30-17:30",None,"9点前最活跃"),
        ("宽窄巷子","成都","青羊区","长顺上街","文创街区",0,0,4.6,90,"商务休闲","老成都底片","宽巷子,窄巷子",None,"全天",None,"下午喝茶晚上泡吧"),
        ("都江堰","成都","都江堰市","公园路","历史古迹",80,90,4.8,180,"商务一日游","世界水利工程鼻祖","宝瓶口,飞沙堰","028-87120836","08:00-18:00",None,"建议请导游"),
        ("洪崖洞","重庆","渝中区","嘉陵江滨江路88号","城市景观",0,0,4.5,90,"商务观光","现实版千与千寻","吊脚楼,江景","023-63039999","全天",None,"千厮门大桥拍"),
        ("西湖","杭州","西湖区","龙井路1号","自然景观",0,0,4.9,240,"商务接待","世界文化景观遗产","断桥残雪,三潭印月","0571-87179617","全天",None,"租自行车环湖"),
        ("黄鹤楼","武汉","武昌区","蛇山西山坡特1号","历史古迹",70,80,4.6,90,"商务观光","天下江山第一楼","登楼望江","027-88877330","08:00-18:00",None,"傍晚看落日"),
        ("秦始皇兵马俑","西安","临潼区","秦陵北路","历史古迹",120,120,4.9,180,"商务文化,高端接待","世界第八大奇迹","一号坑,铜车马","029-81399174","08:30-18:00","可约VIP讲解","请专业讲解"),
        ("中山陵","南京","玄武区","中山陵石象路7号","历史古迹",0,0,4.8,120,"商务文化","孙中山先生陵寝","博爱坊,陵门","025-84431991","08:30-17:00","需预约","免费但需预约"),
        ("岳麓山","长沙","岳麓区","麓山路","自然景观",0,0,4.6,120,"商务休闲","湖湘文化发源地","爱晚亭,岳麓书院","0731-88822539","06:00-23:00",None,"秋天红叶最美"),
        ("滇池","昆明","西山区","滇池路1318号","自然景观",0,0,4.5,120,"商务休闲","云南最大高原湖泊","西山龙门,海埂公园","0871-64312083","全天",None,"冬季有红嘴鸥"),
    ]
    for a in attractions:
        db.execute("INSERT INTO attractions (name,city,district,address,category,price_min,price_max,rating,duration_min,scene_tags,description,highlights,contact_phone,opening_hours,reserve_note,tips) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", a)
    print(f"Attractions: {len(attractions)}")
else:
    print(f"Attractions: {cnt} (skip)")

# === Shopping ===
db.executescript("""
CREATE TABLE IF NOT EXISTS shopping_venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, city TEXT NOT NULL, district TEXT, address TEXT NOT NULL,
    shop_type TEXT DEFAULT 'gift', categories TEXT DEFAULT '[]',
    price_min INTEGER, price_max INTEGER, rating REAL DEFAULT 4.0,
    scene_tags TEXT DEFAULT '[]', description TEXT,
    highlights TEXT DEFAULT '[]', contact_phone TEXT,
    opening_hours TEXT DEFAULT '10:00-22:00', reserve_note TEXT,
    data_source TEXT DEFAULT 'seed',
    created_at TEXT DEFAULT (datetime('now','localtime'))
)
""")
cnt = db.execute("SELECT count(*) FROM shopping_venues").fetchone()[0]
if cnt == 0:
    shops = [
        ("同仁堂","北京","东城区","前门大栅栏24号","老字号","中药,保健品",100,5000,4.7,"商务礼品","三百年中药老字号","安宫牛黄丸","010-63031155","08:30-17:30",None),
        ("荣宝斋","北京","西城区","琉璃厂西街19号","老字号","文房四宝,字画",200,50000,4.8,"高端商务礼品","三百年文房名店","木版水印","010-63035279","09:00-17:30","定制需预约"),
        ("上海第一食品商店","上海","黄浦区","南京东路720号","特产","食品礼盒",100,2000,4.5,"商务伴手礼","上海特产一站购","老上海礼盒","021-63222777","09:30-21:00",None),
        ("广州酒家礼饼","广州","荔湾区","文昌南路2号","老字号","食品礼盒",100,500,4.6,"商务伴手礼","中华老字号","广式月饼","020-81380388","09:00-21:00","月饼提前1月"),
        ("蜀绣博物馆商店","成都","青羊区","草堂东路2号","特产","蜀绣,工艺品",200,10000,4.7,"高端商务礼品","蜀绣非遗传承","蜀绣熊猫","028-87371140","09:00-17:00","定制需1月"),
        ("竹叶青旗舰店","成都","武侯区","科华中路9号","特产","茶叶",100,3000,4.6,"商务礼品","峨眉高山绿茶","论道级竹叶青","028-85221122","09:00-21:00",None),
        ("万事利丝绸","杭州","拱墅区","凤起路268号","特产","丝绸",200,5000,4.5,"商务礼品","中国丝绸之府","万事利丝绸","0571-85801888","09:00-17:30",None),
        ("云南普洱茶城","昆明","官渡区","康乐茶文化城","特产","茶叶",50,5000,4.5,"商务礼品","普洱茶原产地","老班章","0871-67178888","09:00-18:00",None),
    ]
    for s in shops:
        db.execute("INSERT INTO shopping_venues (name,city,district,address,shop_type,categories,price_min,price_max,rating,scene_tags,description,highlights,contact_phone,opening_hours,reserve_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", s)
    print(f"Shopping: {len(shops)}")
else:
    print(f"Shopping: {cnt} (skip)")

db.commit()
db.close()

# Summary
db2 = sqlite3.connect(DB)
print("\n=== Final Summary ===")
for t in ['restaurants','services','transport_routes','hotels','attractions','shopping_venues']:
    try:
        cnt = db2.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
        cities = db2.execute(f'SELECT count(DISTINCT city) FROM {t}').fetchone()[0]
        print(f'  {t:20s}: {cnt:>5} rows, {cities} cities')
    except:
        print(f'  {t:20s}: NOT FOUND')
db2.close()
