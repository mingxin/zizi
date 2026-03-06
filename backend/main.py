import os
import json
import random
import base64
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional

# 加载 .env 文件中的环境变量
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import httpx

# 导入认证和数据库模块
from auth import (
    register_user, login_user, refresh_access_token,
    get_current_user, User, TokenResponse, verify_token, decode_token
)
from database.db import init_database, execute_query, execute_insert

app = FastAPI(title="zizi AI识字伴侣 API", docs_url="/docs", redoc_url="/redoc")

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    init_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 调试端点 - 用于测试连接
@app.get("/api/debug")
async def debug():
    return {"status": "ok", "message": "Backend is running"}


# ==================== 认证接口 ====================

@app.post("/api/auth/register")
async def api_register(request: Request):
    """用户注册"""
    try:
        data = await request.json()
        phone = data.get("phone")
        password = data.get("password")

        if not phone or not password:
            raise HTTPException(status_code=400, detail="手机号和密码不能为空")

        result = register_user(phone, password)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def api_login(request: Request):
    """用户登录"""
    try:
        data = await request.json()
        phone = data.get("phone")
        password = data.get("password")

        if not phone or not password:
            raise HTTPException(status_code=400, detail="手机号和密码不能为空")

        result = login_user(phone, password)
        if "error" in result:
            raise HTTPException(status_code=401, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/refresh", response_model=TokenResponse)
async def api_refresh(request: Request):
    """刷新Token"""
    try:
        data = await request.json()
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            raise HTTPException(status_code=400, detail="刷新令牌不能为空")

        result = refresh_access_token(refresh_token)
        if "error" in result:
            raise HTTPException(status_code=401, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/logout")
async def api_logout(current_user: User = Depends(get_current_user)):
    """用户登出"""
    # 客户端删除token即可，服务端无状态
    return {"success": True, "message": "已登出"}


@app.get("/api/user/profile")
async def api_get_profile(current_user: User = Depends(get_current_user)):
    """获取用户信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    # current_user 是字典，不是对象
    return {
        "id": current_user.get("user_id"),
        "phone": current_user.get("phone"),
        "nickname": None,
        "created_at": None,
        "last_login_at": None
    }


@app.get("/api/user/stats")
async def api_get_stats(current_user: User = Depends(get_current_user)):
    """获取用户学习统计"""
    # 查询学习记录统计
    stats = execute_query(
        """SELECT
            COUNT(DISTINCT char) as total_chars,
            COUNT(*) as total_records,
            SUM(duration_sec) as total_duration
        FROM learning_records
        WHERE user_id = ?""",
        (current_user.id,),
        fetch_one=True
    )

    # 查询最近学习的字
    recent_chars = execute_query(
        """SELECT char, MAX(created_at) as last_time
        FROM learning_records
        WHERE user_id = ?
        GROUP BY char
        ORDER BY last_time DESC
        LIMIT 10""",
        (current_user.id,)
    )

    return {
        "stats": stats or {"total_chars": 0, "total_records": 0, "total_duration": 0},
        "recent_chars": recent_chars
    }


# ==================== 原有功能 ====================

CHARACTERS = [
    "日",
    "月",
    "水",
    "火",
    "口",
    "目",
    "耳",
    "手",
    "足",
    "山",
    "石",
    "田",
    "禾",
    "猫",
    "狗",
    "鸟",
    "鱼",
]

INFANT_WORDS = [
    "一",
    "二",
    "三",
    "人",
    "大",
    "小",
    "上",
    "下",
    "中",
    "口",
    "手",
    "足",
    "目",
    "耳",
    "口",
    "日",
    "月",
    "水",
    "火",
    "山",
    "石",
    "田",
    "土",
    "木",
    "天",
    "地",
    "云",
    "雨",
    "风",
    "雪",
    "花",
    "草",
    "树",
    "叶",
    "果",
    "瓜",
    "米",
    "豆",
    "瓜",
    "菜",
    "犬",
    "猫",
    "鸟",
    "鱼",
    "虫",
    "马",
    "牛",
    "羊",
    "猪",
    "兔",
    "父",
    "母",
    "子",
    "女",
    "男",
    "女",
    "老",
    "少",
    "头",
    "面",
    "心",
    "血",
    "骨",
    "肉",
    "皮",
    "毛",
    "血",
    "气",
    "力",
    "大",
    "长",
    "短",
    "高",
    "低",
    "多",
    "少",
    "好",
    "坏",
    "新",
    "旧",
    "白",
    "黑",
    "红",
    "黄",
    "蓝",
    "绿",
    "青",
    "紫",
    "灰",
    "白",
    "来",
    "去",
    "出",
    "入",
    "进",
    "退",
    "远",
    "近",
    "前",
    "后",
]

TODDLER_WORDS = INFANT_WORDS + [
    "千",
    "万",
    "百",
    "十",
    "个",
    "十",
    "半",
    "些",
    "点",
    "条",
    "本",
    "块",
    "件",
    "张",
    "把",
    "只",
    "匹",
    "头",
    "条",
    "颗",
    "粒",
    "滴",
    "片",
    "层",
    "段",
    "节",
    "排",
    "组",
    "堆",
    "串",
    "天",
    "年",
    "月",
    "日",
    "时",
    "分",
    "秒",
    "春",
    "夏",
    "秋",
    "冬",
    "今",
    "明",
    "昨",
    "早",
    "晚",
    "中",
    "午",
    "夜",
    "朝",
    "东",
    "西",
    "南",
    "北",
    "左",
    "右",
    "旁",
    "边",
    "角",
    "面",
    "事",
    "时",
    "物",
    "体",
    "心",
    "意",
    "情",
    "感",
    "思",
    "念",
    "学",
    "习",
    "读",
    "写",
    "画",
    "唱",
    "跳",
    "跑",
    "走",
    "坐",
    "立",
    "躺",
    "卧",
    "跑",
    "跳",
    "爬",
    "坐",
    "站",
    "走",
    "跑",
    "吃",
    "喝",
    "睡",
    "醒",
    "哭",
    "笑",
    "说",
    "听",
    "看",
    "闻",
    "爱",
    "喜",
    "欢",
    "恨",
    "怕",
    "惊",
    "急",
    "气",
    "乐",
    "悲",
    "公",
    "母",
    "父",
    "母",
    "哥",
    "弟",
    "姐",
    "妹",
    "叔",
    "姨",
    "爷",
    "奶",
    "祖",
    "外",
    "姑",
    "舅",
    "伯",
    "表",
    "亲",
    "朋",
    "家",
    "门",
    "窗",
    "床",
    "桌",
    "椅",
    "椅",
    "沙",
    "发",
    "柜",
    "衣",
    "服",
    "裤",
    "裙",
    "鞋",
    "帽",
    "袜",
    "巾",
    "裙",
    "衫",
    "饭",
    "粥",
    "面",
    "包",
    "饼",
    "糖",
    "果",
    "奶",
    "茶",
    "水",
    "车",
    "船",
    "飞",
    "机",
    "火",
    "车",
    "汽",
    "车",
    "自",
    "行",
    "刀",
    "剑",
    "枪",
    "炮",
    "弓",
    "盾",
    "旗",
    "鼓",
    "铃",
    "钟",
    "纸",
    "笔",
    "墨",
    "书",
    "画",
    "琴",
    "笛",
    "箫",
    "鼓",
    "锣",
    "金",
    "银",
    "铜",
    "铁",
    "锡",
    "铝",
    "锌",
    "钢",
    "链",
    "针",
    "城",
    "墙",
    "房",
    "屋",
    "楼",
    "塔",
    "桥",
    "路",
    "街",
    "道",
    "河",
    "湖",
    "海",
    "江",
    "溪",
    "泉",
    "井",
    "渠",
    "坝",
    "塘",
    "林",
    "草",
    "原",
    "野",
    "田",
    "园",
    "花",
    "木",
    "竹",
    "松",
    "鸡",
    "鸭",
    "鹅",
    "鸟",
    "兽",
    "畜",
    "狼",
    "狐",
    "熊",
    "豹",
    "虎",
    "狮",
    "象",
    "马",
    "驴",
    "骡",
    "骆",
    "驼",
    "牛",
    "羊",
]

CHILD_WORDS = TODDLER_WORDS + [
    "百",
    "千",
    "万",
    "亿",
    "兆",
    "京",
    "垓",
    "秭",
    "穰",
    "沟",
    "静",
    "动",
    "快",
    "慢",
    "早",
    "迟",
    "久",
    "暂",
    "常",
    "偶",
    "真",
    "假",
    "实",
    "虚",
    "明",
    "暗",
    "清",
    "浊",
    "洁",
    "脏",
    "温",
    "凉",
    "热",
    "冷",
    "暖",
    "寒",
    "暑",
    "燥",
    "湿",
    "润",
    "甘",
    "苦",
    "酸",
    "辣",
    "咸",
    "甜",
    "香",
    "臭",
    "腥",
    "臊",
    "美",
    "丑",
    "俊",
    "俏",
    "雅",
    "俗",
    "贵",
    "贱",
    "富",
    "贫",
    "强",
    "弱",
    "勇",
    "怯",
    "智",
    "愚",
    "贤",
    "愚",
    "圣",
    "凡",
    "善",
    "恶",
    "正",
    "邪",
    "忠",
    "奸",
    "忠",
    "孝",
    "仁",
    "义",
    "礼",
    "智",
    "信",
    "诚",
    "谦",
    "傲",
    "谦",
    "让",
    "忍",
    "耐",
    "宽",
    "严",
    "慈",
    "严",
    "亲",
    "疏",
    "密",
    "疏",
    "聚",
    "散",
    "升",
    "降",
    "浮",
    "沉",
    "起",
    "落",
    "升",
    "降",
    "涨",
    "退",
    "始",
    "终",
    "古",
    "今",
    "往",
    "来",
    "过",
    "去",
    "将",
    "就",
    "已",
    "曾",
    "正",
    "将",
    "已",
    "未",
    "便",
    "即",
    "立",
    "刻",
    "常",
    "时",
    "刻",
    "瞬",
    "刹",
    "须",
    "臾",
    "刻",
    "分",
    "秒",
    "永",
    "久",
    "长",
    "短",
    "永",
    "恒",
    "瞬",
    "息",
    "瞬",
    "万",
    "宇",
    "宙",
    "空",
    "间",
    "维",
    "度",
    "时",
    "空",
    "宇",
    "宙",
    "太",
    "阳",
    "月",
    "亮",
    "星",
    "辰",
    "天",
    "体",
    "星",
    "辰",
    "光",
    "热",
    "能",
    "量",
    "电",
    "磁",
    "力",
    "热",
    "光",
    "声",
    "形",
    "色",
    "音",
    "声",
    "味",
    "香",
    "触",
    "感",
    "觉",
    "悟",
    "思",
    "想",
    "念",
    "思",
    "维",
    "意",
    "识",
    "心",
    "灵",
    "魂",
    "精",
    "神",
    "气",
    "血",
    "体",
    "魄",
    "魂",
    "魄",
    "灵",
    "魂",
    "天",
    "命",
    "运",
    "气",
    "数",
    "理",
    "道",
    "法",
    "术",
    "技",
    "学",
    "问",
    "知",
    "识",
    "智",
    "慧",
    "聰",
    "明",
    "睿",
    "哲",
    "理",
    "学",
    "科",
    "技",
    "术",
    "艺",
    "文",
    "化",
    "明",
    "理",
    "教",
    "育",
    "培",
    "养",
    "训",
    "练",
    "学",
    "习",
    "研",
    "究",
    "读",
    "写",
    "算",
    "画",
    "唱",
    "跳",
    "跑",
    "踢",
    "打",
    "球",
    "游",
    "戏",
    "玩",
    "乐",
    "趣",
    "味",
    "欣",
    "赏",
    "娱乐",
    "休闲",
    "工",
    "作",
    "事",
    "业",
    "职",
    "业",
    "岗",
    "位",
    "责",
    "任",
    "务",
    "劳",
    "动",
    "努",
    "力",
    "奋",
    "斗",
    "拼",
    "搏",
    "进",
    "取",
    "创",
    "新",
    "发",
    "展",
    "进",
    "步",
    "成",
    "长",
    "成",
    "功",
    "失",
    "败",
    "胜",
    "负",
    "荣",
    "辱",
    "奖",
    "惩",
    "罚",
    "法",
    "律",
    "规",
    "则",
    "制",
    "度",
    "秩",
    "序",
    "安",
    "定",
    "和",
    "平",
    "安",
    "宁",
    "静",
    "安",
    "泰",
    "平",
    "安",
    "福",
    "祸",
    "福",
    "吉",
    "凶",
    "祥",
    "瑞",
    "祸",
    "福",
    "灾",
    "难",
    "生",
    "死",
    "存",
    "亡",
    "活",
    "死",
    "生",
    "命",
    "寿",
    "终",
    "青",
    "春",
    "年",
    "老",
    "少",
    "壮",
    "幼",
    "童",
    "青",
    "老",
    "婚",
    "嫁",
    "娶",
    "配",
    "恋",
    "爱",
    "情",
    "婚",
    "姻",
    "家",
    "庭",
    "父",
    "母",
    "夫",
    "妻",
    "子",
    "女",
    "兄",
    "弟",
    "姐",
    "妹",
    "亲",
    "友",
    "邻",
    "同",
    "事",
    "伙",
    "伴",
    "师",
    "生",
    "同",
    "学",
    "校",
    "友",
    "师",
    "长",
    "领",
    "导",
    "群",
    "众",
    "人",
    "民",
    "群",
    "众",
    "众",
    "人",
    "群",
    "体",
    "国",
    "家",
    "党",
    "政",
    "军",
    "民",
    "学",
    "商",
    "工",
    "农",
    "兵",
    "学",
    "科",
    "研",
    "究",
    "文",
    "体",
    "卫",
    "生",
    "财",
    "经",
    "贸",
    "工",
    "业",
    "农",
    "业",
    "商",
    "业",
    "渔",
    "业",
    "林",
    "业",
    "牧",
    "业",
    "航",
    "空",
    "航",
    "天",
    "海",
    "运",
    "陆",
    "运",
    "铁",
    "路",
    "公",
    "路",
    "高速",
    "高速",
    "隧",
    "道",
    "桥",
    "梁",
    "港",
    "口",
    "码",
    "头",
    "机",
    "场",
    "车",
    "站",
    "港",
    "湾",
]

TEEN_WORDS = CHILD_WORDS + [
    "函",
    "曲",
    "故",
    "事",
    "小",
    "说",
    "散",
    "文",
    "诗",
    "词",
    "曲",
    "赋",
    "戏",
    "剧",
    "音",
    "乐",
    "舞",
    "蹈",
    "美",
    "术",
    "雕",
    "塑",
    "摄",
    "影",
    "书",
    "法",
    "绘",
    "画",
    "工",
    "艺",
    "技",
    "术",
    "科",
    "学",
    "研",
    "究",
    "发",
    "明",
    "创",
    "造",
    "改",
    "革",
    "变",
    "革",
    "进",
    "步",
    "发",
    "展",
    "成",
    "长",
    "历",
    "史",
    "文",
    "明",
    "文",
    "化",
    "传",
    "统",
    "遗",
    "产",
    "古",
    "代",
    "现",
    "代",
    "当",
    "代",
    "近",
    "代",
    "远",
    "古",
    "上",
    "古",
    "中",
    "古",
    "近",
    "古",
    "古",
    "史",
    "今",
    "史",
    "世",
    "界",
    "环",
    "球",
    "宇",
    "宙",
    "天",
    "地",
    "人",
    "神",
    "鬼",
    "灵",
    "魂",
    "魄",
    "精",
    "神",
    "体",
    "形",
    "象",
    "征",
    "寓",
    "言",
    "童",
    "话",
    "神",
    "话",
    "传",
    "说",
    "民",
    "间",
    "故",
    "事",
    "历",
    "险",
    "奇",
    "遇",
    "梦",
    "幻",
    "虚",
    "构",
    "想",
    "象",
    "创",
    "意",
    "灵",
    "感",
    "思",
    "路",
    "构",
    "思",
    "设",
    "计",
    "规",
    "划",
    "筹",
    "备",
    "组",
    "织",
    "领",
    "导",
    "管",
    "理",
    "经",
    "营",
    "运",
    "作",
    "决",
    "策",
    "计",
    "划",
    "目",
    "标",
    "方",
    "针",
    "原",
    "则",
    "理",
    "念",
    "信",
    "念",
    "理",
    "想",
    "志",
    "向",
    "抱",
    "负",
    "理",
    "想",
    "梦",
    "想",
    "志",
    "愿",
    "愿",
    "望",
    "期",
    "望",
    "盼",
    "望",
    "期",
    "待",
    "愿",
    "意",
    "情",
    "愿",
    "甘",
    "愿",
    "宁",
    "愿",
    "肯",
    "定",
    "必",
    "须",
    "该",
    "当",
    "应",
    "该",
    "理",
    "应",
    "当",
    "然",
    "必",
    "然",
    "当",
    "然",
    "突",
    "然",
    "竟",
    "然",
    "居",
    "然",
    "到",
    "底",
    "究",
    "竟",
    "到",
    "底",
    "终",
    "究",
    "竟",
    "究",
    "到",
    "底",
    "究",
    "竟",
    "底",
    "竟",
    "底",
    "细",
    "根",
    "本",
    "原",
    "本",
    "正",
    "本",
    "原",
    "始",
    "起",
    "源",
    "根",
    "源",
    "原",
    "因",
    "起",
    "因",
    "缘",
    "故",
    "缘",
    "由",
    "缘",
    "故",
    "缘",
    "分",
    "机",
    "缘",
    "因",
    "缘",
    "果",
    "报",
    "因",
    "果",
    "报",
    "应",
    "果",
    "报",
    "因",
    "果",
    "报",
    "应",
    "报",
    "应",
    "轮",
    "回",
    "宿",
    "命",
    "命",
    "运",
    "气",
    "数",
    "定",
    "数",
    "命",
    "定",
    "天",
    "命",
    "宿",
    "命",
    "命",
    "运",
    "命",
    "定",
    "天",
    "定",
    "听",
    "天",
    "听",
    "命",
    "天",
    "定",
    "听",
    "命",
    "自然",
    "天然",
    "自然",
    "天赋",
    "天性",
    "天性",
    "本性",
    "本性",
    "本",
    "性",
    "天",
    "性",
    "禀",
    "性",
    "性",
    "情",
    "性",
    "格",
    "性",
    "情",
    "脾",
    "气",
    "性",
    "情",
    "性",
    "格",
    "气",
    "质",
    "气",
    "质",
    "秉",
    "性",
    "气",
    "性",
    "天",
    "性",
    "纯",
    "真",
    "纯",
    "洁",
    "纯",
    "真",
    "纯",
    "朴",
    "朴",
    "素",
    "朴",
    "实",
    "朴",
    "实",
    "诚",
    "实",
    "诚",
    "恳",
    "诚",
    "信",
    "诚",
    "意",
    "诚",
    "心",
    "诚",
    "挚",
    "真",
    "诚",
    "真",
    "挚",
    "真",
    "心",
    "真",
    "情",
    "真",
    "爱",
    "真",
    "心",
    "挚",
    "爱",
    "挚",
    "情",
    "热",
    "爱",
    "热",
    "情",
    "热",
    "心",
    "热",
    "烈",
    "炽",
    "热",
    "火",
    "热",
    "热",
    "情",
    "激",
    "情",
    "情",
    "感",
    "情",
    "绪",
    "情",
    "绪",
    "感",
    "情",
    "感",
    "动",
    "感",
    "恩",
    "感",
    "激",
    "感",
    "谢",
    "感",
    "悟",
    "感",
    "觉",
    "感",
    "受",
    "体会",
    "体会",
    "体",
    "验",
    "体",
    "会",
    "感",
    "同",
    "感",
    "同",
    "身受",
    "感同",
    "身",
    "临",
    "感",
    "同",
    "身",
    "受",
    "如",
    "同",
    "如同",
    "好像",
    "似乎",
    "好像",
    "仿佛",
    "类",
    "似",
    "类",
    "似",
    "相",
    "似",
    "相",
    "像",
    "相",
    "似",
    "相",
    "同",
    "相",
    "近",
    "相",
    "差",
    "相",
    "差",
    "差",
    "别",
    "区",
    "别",
    "差",
    "距",
    "差",
    "异",
    "差",
    "异",
    "不",
    "同",
    "不",
    "异",
    "差",
    "别",
    "悬",
    "殊",
    "天",
    "壤",
    "天",
    "地",
    "差",
    "别",
    "差",
    "距",
    "相",
    "反",
    "相",
    "对",
    "相",
    "反",
    "相",
    "对",
    "相",
    "对",
    "相",
    "比",
    "比",
    "拟",
    "比",
    "较",
    "比",
    "对",
    "比",
    "拼",
    "比",
    "赛",
    "比",
    "武",
    "竞",
    "争",
    "竞",
    "赛",
    "比",
    "拼",
    "竞",
    "技",
    "竞",
    "技",
    "争",
    "先",
    "争",
    "夺",
    "抢",
    "占",
    "抢",
    "劫",
    "抢",
    "夺",
    "争",
    "斗",
    "战",
    "斗",
    "战",
    "争",
    "战",
    "斗",
    "战",
    "争",
    "战",
    "役",
    "战",
    "争",
    "战",
    "斗",
    "斗争",
    "战斗",
    "斗",
    "争",
    "战",
    "斗",
    "战",
    "役",
    "战",
    "争",
    "战",
    "略",
    "战",
    "术",
    "策",
    "略",
    "计",
    "谋",
    "策",
    "略",
    "计",
    "策",
    "谋",
    "略",
    "计",
    "谋",
    "策",
    "划",
    "谋",
    "策",
    "计",
    "划",
    "谋",
    "划",
    "策",
    "划",
    "筹",
    "划",
    "筹",
    "备",
    "筹",
    "措",
    "筹",
    "措",
    "筹",
    "备",
    "安",
    "排",
    "布",
    "置",
    "布",
    "置",
    "安",
    "排",
    "布",
    "局",
    "布",
    "置",
    "摆",
    "设",
    "摆",
    "放",
    "放",
    "置",
    "安",
    "放",
    "摆",
    "放",
    "存",
    "放",
    "储",
    "藏",
    "储",
    "藏",
    "储",
    "备",
    "保",
    "存",
    "保",
    "管",
    "保",
    "护",
    "保",
    "守",
    "保",
    "留",
    "保",
    "全",
    "保",
    "安",
    "保",
    "险",
    "保",
    "修",
    "保",
    "养",
    "保",
    "持",
    "保",
    "持",
    "维",
    "持",
    "维",
    "护",
    "维",
    "修",
    "维",
    "持",
    "养",
    "护",
    "修",
    "养",
    "修",
    "理",
    "修",
    "复",
    "修",
    "补",
    "修",
    "建",
    "修",
    "造",
]

WORD_LIBRARIES = {
    "infant": {
        "id": "infant",
        "name": "幼儿组",
        "description": "100字 - 笔画最简单的常用字",
        "words": INFANT_WORDS[:100],
        "word_count": 100,
    },
    "toddler": {
        "id": "toddler",
        "name": "小儿组",
        "description": "500字 - 笔画简单的常用字",
        "words": TODDLER_WORDS[:500],
        "word_count": 500,
    },
    "child": {
        "id": "child",
        "name": "儿童组",
        "description": "1000字 - 笔画稍复杂的常用字",
        "words": CHILD_WORDS[:1000],
        "word_count": 1000,
    },
    "teen": {
        "id": "teen",
        "name": "少年组",
        "description": "1500字 - 笔画较复杂的常用字",
        "words": TEEN_WORDS[:1500],
        "word_count": 1500,
    },
}

VOICES = {
    "serena": {
        "id": "serena",
        "name": "苏瑶",
        "description": "甜美女声",
        "language": "zh-CN",
        "style": "happy",
        "speed": 0.9,
    },
    "maia": {
        "id": "maia",
        "name": "四月",
        "description": "活泼女声",
        "language": "zh-CN",
        "style": "cheerful",
        "speed": 1.0,
    },
    "rocky": {
        "id": "rocky",
        "name": "粤语-阿强",
        "description": "低沉男声",
        "language": "zh-CN",
        "style": "default",
        "speed": 0.9,
    },
    "kiki": {
        "id": "kiki",
        "name": "粤语-阿清",
        "description": "温柔女声",
        "language": "zh-CN",
        "style": "default",
        "speed": 0.9,
    },
    "browser": {
        "id": "browser",
        "name": "浏览器语音",
        "description": "使用浏览器内置语音",
        "language": "zh-CN",
        "style": "default",
        "speed": 0.8,
    },
}

STORY_TEMPLATES = {
    "日": "哇！{object}圆圆的，像不像太阳？太阳每天早上从东边升起来，照得我们暖洋洋的！你好呀，小太阳！",
    "月": "哇！我看到{object}啦！月亮婆婆晚上出来，弯弯的时候像小船，圆圆的时候像大盘子。你见过月亮吗？",
    "水": "哎呀，{object}里面有水！水是无色无味的好朋友，我们每天都要喝水，这样才能健康成长！",
    "火": "咦？{object}红红的，像不像一把火？火可以让我们暖和，还可以煮好吃的饭菜。但是要小心火哦！",
    "口": "看！{object}张着大嘴巴！口字就像我们的小嘴巴，能吃东西，还能说话。你会说什么呀？",
    "目": "哇！{object}上有两个小圆点，像眼睛一样！目字就是眼睛的意思，我们用眼睛看世界、交朋友！",
    "耳": "这个{object}好像耳朵呀！耳朵是用来听声音的，听妈妈讲故事，听小鸟唱歌。你听到了什么？",
    "手": "哇！{object}旁边有手！我们用 手拿东西、玩游戏、抱抱爸爸妈妈。手有五个手指头！",
    "足": "看，{object}下面有脚！足字就是脚的意思。我们用脚走路、跑步、踢球。小脚丫真厉害！",
    "山": "这个{object}高高的，像不像一座山？山上有树、有花，还有可爱的小动物。你爬过山吗？",
    "石": "哇！{object}硬邦邦的，像石头一样！石头可以用来搭房子，还能铺路。小石子真有用！",
    "田": "看这个{object}，四四方方的，像不像田地？农民伯伯在田里种粮食，我们才能吃到香喷喷的米饭！",
    "禾": "哇！{object}下面有禾苗！禾是稻子的意思，秋天的时候稻子成熟了，我们就有了大米吃！",
    "猫": "喵喵喵！一只可爱的小{object}！猫的嘴巴两边有胡须，夜晚眼睛会发光。你喜欢小猫吗？",
    "狗": "汪汪汪！一只小{object}来啦！狗是人类的好朋友，会帮我们看家，还能陪我们玩耍！",
    "鸟": "看！一只小{object}在天上飞！鸟儿有翅膀，会唱歌，还会筑巢。小鸟，你好呀！",
    "鱼": "哇！水里有一只小{object}！鱼有鳞片，会游泳，还会吐泡泡。小鱼游啊游，真快活！",
}

DEMO_STORIES = [
    "哎呀，这个东西真有趣！让zizi想想...这个字是'日'，太阳的日！每天早上，太阳公公就出来啦！",
    "哇！这个东西好特别！zizi想到了'月'字，月亮婆婆晚上出来，弯弯的像小船！",
    "嗯...让zizi想一想...这个是'口'字！口字就像我们的小嘴巴，能吃东西还能说话！",
    "哇！我知道啦！这个字是'手'！我们用手拿东西、玩游戏，手有五个手指头！",
]


def get_mock_result(image_data: bytes, library_words: list = None) -> dict:
    """Demo mode - generate mock result without real API calls"""
    if library_words is None:
        library_words = CHARACTERS

    try:
        image = Image.open(BytesIO(image_data))
        width, height = image.size

        dominant_color = image.getpixel((width // 2, height // 2)) or (200, 150, 100)

        if isinstance(dominant_color, tuple):
            r, g, b = dominant_color[:3]
            if r > 150 and g < 100 and b < 100:
                char = "火"
            elif g > 150 and r < 100:
                char = "水"
            elif r > 200 and g > 150:
                char = "日"
            else:
                char = random.choice(library_words)
        else:
            char = random.choice(library_words)
    except Exception:
        char = random.choice(library_words)

    story_template = STORY_TEMPLATES.get(
        char, "哇！这个{object}真有趣！zizi想到了{char}这个字！"
    )
    story = story_template.format(object="这个东西", char=char)

    if random.random() > 0.5:
        story = random.choice(DEMO_STORIES)

    return {
        "target_char": char,
        "story_text": story,
        "mood": random.choice(["excited", "happy", "curious"]),
        "audio_url": None,
    }


@app.get("/")
async def root():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>zizi AI识字伴侣</title>
        <style>
            body {
                font-family: 'Comic Sans MS', 'Chalkboard SE', sans-serif;
                background: linear-gradient(135deg, #FFF5F5 0%, #F8F9FA 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 20px;
            }
            h1 {
                color: #FF6B6B;
                font-size: 3rem;
                margin-bottom: 10px;
            }
            p {
                color: #2C3E50;
                font-size: 1.2rem;
                margin-bottom: 30px;
            }
            .links {
                display: flex;
                gap: 20px;
            }
            a {
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #4ECDC4 0%, #6EE7DE 100%);
                color: white;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                transition: transform 0.2s;
            }
            a:hover {
                transform: scale(1.05);
            }
            .status {
                margin-top: 40px;
                color: #888;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <h1>zizi AI识字伴侣</h1>
        <p>3-6岁儿童的AI识字伙伴</p>
        <div class="links">
            <a href="/docs">API 文档</a>
            <a href="http://192.168.3.110:3000">打开前端</a>
        </div>
        <div class="status">API Status: Running ✓</div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    word_library: str = Form("infant"),
    voice_id: str = Form("serena"),
    authorization: str = Form(None),  # 可选的登录token
):
    """Process uploaded image and return character + story with pre-generated TTS"""
    try:
        image_data = await file.read()
        print(f"Received image: filename={file.filename}, size={len(image_data)}")

        if not image_data or len(image_data) == 0:
            raise HTTPException(status_code=400, detail="图片为空")

        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片太大了")

        print(f"word_library={word_library}, voice_id={voice_id}")
        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
        print(f"API key loaded: {bool(api_key)}")

        library = WORD_LIBRARIES.get(word_library, WORD_LIBRARIES["infant"])
        library_words = library.get("words", WORD_LIBRARIES["infant"]["words"])

        if api_key:
            result = await call_ai_api(image_data, api_key, library_words)

            char = result.get("target_char", "")
            story_text = result.get("story_text", "")

            audio_url = None
            char_audio_url = None

            if story_text and story_text != "哇！这个真有趣！":
                tts_task = asyncio.create_task(
                    generate_tts_async(story_text, voice_id, api_key)
                )
                try:
                    audio_url = await asyncio.wait_for(tts_task, timeout=10.0)
                except asyncio.TimeoutError:
                    print("TTS story generation timeout")
                except Exception as e:
                    print(f"TTS story generation failed: {e}")

            if char:
                char_tts_task = asyncio.create_task(
                    generate_tts_async(char, voice_id, api_key)
                )
                try:
                    char_audio_url = await asyncio.wait_for(char_tts_task, timeout=8.0)
                except asyncio.TimeoutError:
                    print("TTS char generation timeout")
                except Exception as e:
                    print(f"TTS char generation failed: {e}")

            result["audio_url"] = audio_url
            result["char_audio_url"] = char_audio_url
        else:
            result = get_mock_result(image_data, library_words)

        # 如果用户已登录，记录学习记录
        user = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]  # 去掉 "Bearer "
            user = verify_token(token)

        if user:
            char = result.get("target_char", "")
            # 记录拍照学习行为
            from database.db import execute_insert
            execute_insert(
                """INSERT INTO learning_records
                   (user_id, char, library_id, action_type, context)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user["id"],
                    char,
                    word_library,
                    "photo_capture",
                    json.dumps({
                        "story_text": result.get("story_text", ""),
                        "voice_id": voice_id,
                        "source": "camera"
                    })
                )
            )
            # 更新或创建汉字掌握度记录
            existing = execute_query(
                "SELECT id, view_count FROM char_mastery WHERE user_id = ? AND char = ?",
                (user["id"], char),
                fetch_one=True
            )
            if existing:
                execute_update(
                    """UPDATE char_mastery
                       SET view_count = view_count + 1, updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (existing["id"],)
                )
            else:
                execute_insert(
                    """INSERT INTO char_mastery (user_id, char, view_count, mastery_level)
                       VALUES (?, ?, 1, 0)""",
                    (user["id"], char)
                )

        return JSONResponse(content=result)

    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error: {e}")
        print(traceback.format_exc())
        # Return more detailed error for debugging
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": error_detail,
                "detail": traceback.format_exc()
            }
        )


@app.get("/api/word-libraries")
async def get_word_libraries():
    """Get all word library groups"""
    libraries = []
    for lib in WORD_LIBRARIES.values():
        libraries.append(
            {
                "id": lib["id"],
                "name": lib["name"],
                "description": lib["description"],
                "word_count": lib["word_count"],
            }
        )
    return JSONResponse(content={"libraries": libraries})


@app.get("/api/word-libraries/{lib_id}")
async def get_word_library(lib_id: str):
    """Get specific word library details"""
    lib = WORD_LIBRARIES.get(lib_id)
    if not lib:
        raise HTTPException(status_code=404, detail="字库不存在")
    return JSONResponse(content=lib)


async def call_ai_api(image_data: bytes, api_key: str, library_words: list) -> dict:
    """Call real AI APIs if configured"""

    word_list_str = "".join(library_words[:80])
    base64_image = base64.b64encode(image_data).decode()

    vision_api = os.getenv("VISION_API", "dashscope")

    if vision_api == "dashscope":
        try:
            async with httpx.AsyncClient() as client:
                vision_response = await client.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "qwen-vl-max",
                        "input": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "image": f"data:image/jpeg;base64,{base64_image}"
                                        },
                                        {
                                            "text": f"""请看这张图片，图片中有什么物体或场景？
                                            
请从以下汉字列表中选择一个最相关的字：{word_list_str}

请用以下JSON格式输出，不要输出其他内容：
{{"char": "选中的汉字", "story": "为这个字编一个50字以内的有趣小故事，要童趣十足，适合3-6岁儿童"}}

例如：如果图片是猫，char可以是"猫"，story是"喵喵喵！一只可爱的小猫！它有长长的胡须，会抓老鼠。你好呀，小猫！" """
                                        },
                                    ],
                                }
                            ]
                        },
                    },
                    timeout=30.0,
                )

                print(f"Dashscope response status: {vision_response.status_code}")

                if vision_response.status_code != 200:
                    print(f"Dashscope error: {vision_response.text}")
                    return get_mock_result(image_data, library_words)

                vision_data = vision_response.json()
                print(f"Dashscope response: {vision_data}")

                content = (
                    vision_data.get("output", {})
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", [])
                )
                if isinstance(content, list) and len(content) > 0:
                    response_text = content[0].get("text", "").strip()
                else:
                    response_text = str(content).strip()

                print(f"LLM response: {response_text}")

                try:
                    import json
                    import re

                    json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        char = result.get("char", random.choice(library_words))
                        story = result.get("story", "哇！这个真有趣！")
                    else:
                        char = (
                            response_text[:4]
                            if response_text
                            else random.choice(library_words)
                        )
                        story = "哇！这个真有趣！"

                    if not char or len(char) > 4:
                        char = random.choice(library_words)

                except Exception as e:
                    print(f"Parse error: {e}, using fallback")
                    char = (
                        response_text[:4]
                        if response_text
                        else random.choice(library_words)
                    )
                    story = "哇！这个真有趣！"

        except Exception as e:
            print(f"Vision API error: {e}")
            return get_mock_result(image_data, library_words)

    else:
        async with httpx.AsyncClient() as client:
            vision_response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""请看这张图片，图片中有什么物体或场景？
请从以下汉字列表中选择一个最相关的字：{word_list_str}
请用以下JSON格式输出：{{"char": "选中的汉字", "story": "50字以内的有趣小故事"}}
例如：{{"char": "猫", "story": "喵喵喵！一只可爱的小猫！它有长长的胡须"}}""",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                    "max_tokens": 200,
                },
                timeout=30.0,
            )

            if vision_response.status_code != 200:
                return get_mock_result(image_data, library_words)

            vision_data = vision_response.json()
            response_text = (
                vision_data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            try:
                import json
                import re

                json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    char = result.get("char", random.choice(library_words))
                    story = result.get("story", "哇！这个真有趣！")
                else:
                    char = (
                        response_text[:4]
                        if response_text
                        else random.choice(library_words)
                    )
                    story = "哇！这个真有趣！"

                if not char or len(char) > 4:
                    char = random.choice(library_words)

            except Exception as e:
                print(f"Parse error: {e}, using fallback")
                char = (
                    response_text[:4] if response_text else random.choice(library_words)
                )
                story = "哇！这个真有趣！"

    return {
        "target_char": char,
        "story_text": story,
        "mood": "excited",
        "audio_url": None,
    }


async def generate_tts_async(text: str, voice_id: str, api_key: str) -> str:
    """Generate TTS audio URL asynchronously"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen3-tts-flash",
                    "input": {"text": text},
                    "parameters": {"voice": voice_id},
                },
                timeout=15.0,
            )

            if response.status_code == 200:
                result = response.json()
                audio_url = result.get("output", {}).get("audio", {}).get("url")
                return audio_url
    except Exception as e:
        print(f"TTS generation error: {e}")

    return None


def map_to_character(description: str) -> str:
    """Map detected object to character"""
    description_lower = description.lower()

    mapping = {
        "cat": "猫",
        "kitten": "猫",
        "小猫": "猫",
        "dog": "狗",
        "puppy": "狗",
        "小狗": "狗",
        "bird": "鸟",
        "小鸟": "鸟",
        "fish": "鱼",
        "小鱼": "鱼",
        "sun": "日",
        "太阳": "日",
        "moon": "月",
        "月亮": "月",
        "water": "水",
        "水": "水",
        "fire": "火",
        "火": "火",
        "mountain": "山",
        "山": "山",
        "rock": "石",
        "石头": "石",
        "eye": "目",
        "眼睛": "目",
        "ear": "耳",
        "耳朵": "耳",
        "hand": "手",
        "手": "手",
        "foot": "足",
        "脚": "足",
        "mouth": "口",
        "嘴巴": "口",
        "field": "田",
        "田": "田",
        "rice": "禾",
        "稻": "禾",
    }

    for key, char in mapping.items():
        if key in description_lower:
            return char

    return random.choice(CHARACTERS)


def generate_story(char: str, description: str) -> str:
    """Generate story based on character"""
    template = STORY_TEMPLATES.get(char, "哇！这个{object}真有趣！")
    return template.format(
        object=description.split("的")[-1] if "的" in description else "这个东西"
    )


@app.get("/api/voices")
async def get_voices():
    """Get available voice options"""
    return JSONResponse(content={"voices": list(VOICES.values())})


@app.post("/api/tts")
async def text_to_speech(text: str = Form(...), voice_id: str = Form("serena")):
    """Convert text to speech"""
    try:
        voice_config = VOICES.get(voice_id, VOICES["serena"])

        if voice_id == "browser":
            return JSONResponse(
                content={
                    "use_browser": True,
                    "voice_id": voice_id,
                    "text": text,
                    "config": voice_config,
                }
            )

        api_key = os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            return JSONResponse(
                content={
                    "use_browser": True,
                    "voice_id": voice_id,
                    "text": text,
                    "error": "No API key configured",
                }
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "qwen3-tts-flash",
                        "input": {
                            "text": text,
                        },
                        "parameters": {
                            "voice": voice_id,
                        },
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    print(f"TTS error: {response.text}")
                    return JSONResponse(
                        content={
                            "use_browser": True,
                            "voice_id": voice_id,
                            "text": text,
                            "error": "TTS generation failed",
                        }
                    )

                result = response.json()
                audio_data = result.get("output", {}).get("audio", {})
                audio_url = audio_data.get("url")

                return JSONResponse(
                    content={
                        "use_browser": False,
                        "voice_id": voice_id,
                        "audio_url": audio_url,
                        "text": text,
                    }
                )

        except Exception as e:
            print(f"TTS exception: {e}")
            return JSONResponse(
                content={
                    "use_browser": True,
                    "voice_id": voice_id,
                    "text": text,
                    "error": str(e),
                }
            )

    except Exception as e:
        print(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts/preview")
async def tts_preview(voice_id: str = Form(...)):
    """Generate preview audio for a voice"""
    try:
        preview_text = "你好啊"

        if voice_id == "browser":
            return JSONResponse(
                content={
                    "use_browser": True,
                    "voice_id": voice_id,
                    "text": preview_text,
                }
            )

        voice_config = VOICES.get(voice_id, VOICES["serena"])
        api_key = os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            return JSONResponse(
                content={
                    "use_browser": True,
                    "voice_id": voice_id,
                    "text": preview_text,
                    "error": "No API key configured",
                }
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "qwen3-tts-flash",
                        "input": {
                            "text": preview_text,
                        },
                        "parameters": {
                            "voice": voice_id,
                        },
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    print(f"TTS preview error: {response.text}")
                    return JSONResponse(
                        content={
                            "use_browser": True,
                            "voice_id": voice_id,
                            "text": preview_text,
                            "error": "TTS generation failed",
                        }
                    )

                result = response.json()
                audio_data = result.get("output", {}).get("audio", {})
                audio_url = audio_data.get("url")

                return JSONResponse(
                    content={
                        "use_browser": False,
                        "voice_id": voice_id,
                        "audio_url": audio_url,
                        "text": preview_text,
                    }
                )

        except Exception as e:
            print(f"TTS preview exception: {e}")
            return JSONResponse(
                content={
                    "use_browser": True,
                    "voice_id": voice_id,
                    "text": preview_text,
                    "error": str(e),
                }
            )

    except Exception as e:
        print(f"TTS preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ============================================
# 用户认证相关接口 (V1.1)
