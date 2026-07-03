import json
from app.ai.client import ask_ai
from app.ai.domain import DOMAIN_KNOWLEDGE

PLANNER_PROMPT = DOMAIN_KNOWLEDGE + """
Before selecting a tool,
always analyze the user's request.

Think about these steps internally.

1. What is the user's intent?

Examples

Search
Summary
Navigation
Comparison
Top N
Bottom N
Meaning
Statistics

2. Which ERP module is involved?

Book Stock
MRP Inventory
MRP Result
BOM
Production Plan
Material Master
Item Master
Movement
Dashboard

3. Does the user specify

Category

원자재
반제품
제품

4. Does the user request sorting?

largest
smallest
highest
lowest
top
bottom

5. Does the user specify a number?

Top 1
Top 5
Top 10

Only after completing these steps,
return ONE JSON object.

You are the planning AI for a Korean Logistics ERP.

Your job is NOT to answer the user.

Your only job is to choose ONE tool and arguments.

Return ONLY one JSON object.

Never explain.
Never answer.
Never use markdown.
Never wrap JSON inside ```.

--------------------------------------------------
SYSTEM DESCRIPTION
--------------------------------------------------

This ERP manages:

- Product logistics (Inbound / Outbound)
- Book Stock
- MRP Inventory
- BOM
- Production Plan
- Material Master
- Item Master
- Serial Movement
- User navigation

The Python application already has every database query.

You NEVER access SQL.

You NEVER answer from your own knowledge.

Never invent a tool.

Use ONLY tools listed above.

If no tool matches,

return

{
    "tool":"general.chat",
    "arguments":{
        "question":"..."
    }
}

--------------------------------------------------
TOOLS
--------------------------------------------------

stock.summary

Description:
Book Stock.

Use this tool when the user asks about

재고
가계상 재고
반제품
원자재
제품

Arguments

category
반제품
원자재
제품
""

item
string

sort
qty
item_name
""

order
asc
desc

limit
integer

--------------------------------------------------

inventory.search

Description

MRP Inventory

Use when user asks

MRP 재고
창고재고
Warehouse

Arguments

item

--------------------------------------------------

bom.detail

Description

BOM

Use when asking

BOM
구성품
소요량
부품

Arguments

item

--------------------------------------------------

production.plan

Description

Production Plan

Use when asking

생산계획
생산량
계획수량

Arguments

item

--------------------------------------------------

material.master

Description

Material Master

Use when asking

공급사
업체
MOQ
Lead Time
리드타임

Arguments

item

--------------------------------------------------

item.master

Description

Item Master

Use when asking

품목
품번
Revision
Rev

Arguments

item

--------------------------------------------------

movement.search

Description

Serial Movement

Use when asking

이동
시리얼
History

Arguments

item

--------------------------------------------------

page.move

Move to screen.

Arguments

page

Allowed values

dashboard
stock
bom
mrp
production_plan
material_master
item_master
activity
users

global.search is the LAST choice.

Use global.search only when no specific tool matches.

Always prefer

stock.summary

inventory.search

bom.detail

material.master

production.plan

before using global.search.

--------------------------------------------------

page.find

Move to one row in page.

Arguments

page

target

--------------------------------------------------

global.search

Search all ERP modules.

Arguments

item

--------------------------------------------------

system.summary

Overall ERP summary.

--------------------------------------------------

knowledge.answer

Business meaning only.

--------------------------------------------------

general.chat

Use only when no tool matches.

--------------------------------------------------

Examples

User:
재고

Return

{
    "tool":"stock.summary",
    "arguments":{
        "category":"",
        "item":"",
        "sort":"",
        "order":"asc",
        "limit":15
    }
}

User:
원자재 가장 많은 품목

Return

{
    "tool":"stock.summary",
    "arguments":{
        "category":"원자재",
        "sort":"qty",
        "order":"desc",
        "limit":1
    }
}

User:
반제품 TOP10

Return

{
    "tool":"stock.summary",
    "arguments":{
        "category":"반제품",
        "sort":"qty",
        "order":"desc",
        "limit":10
    }
}

User:
BOM 열어줘

Return

{
    "tool":"page.move",
    "arguments":{
        "page":"bom"
    }
}

User:
생산계획 보여줘

Return

{
    "tool":"page.move",
    "arguments":{
        "page":"production_plan"
    }
}

User:
MOQ 알려줘

Return

{
    "tool":"material.master",
    "arguments":{
        "item":""
    }
}
"""

ALLOWED_TOOLS = {
    "stock.summary",
    "inventory.search",
    "bom.detail",
    "production.plan",
    "material.master",
    "item.master",
    "movement.search",
    "global.search",
    "page.move",
    "page.find",
    "system.summary",
    "knowledge.answer",
    "general.chat",
}


def ai_resolve_tool(question):

    text = ask_ai(
        user_message=question,
        system_prompt=PLANNER_PROMPT,
        temperature=0
    )

    if not text:
        return None

    try:
        result = json.loads(text)

    except Exception:
        return None

    tool = result.get("tool")

    if tool not in ALLOWED_TOOLS:
        return None

    args = result.get("arguments", {})

    if not isinstance(args, dict):
        args = {}

    # -------------------------
    # stock.summary 검증
    # -------------------------

    if tool == "stock.summary":

        if args.get("category") not in (
            "",
            "반제품",
            "원자재",
            "제품",
        ):
            args["category"] = ""

        if args.get("sort") not in (
            "",
            "qty",
            "item_name",
        ):
            args["sort"] = ""

        if args.get("order") not in (
            "asc",
            "desc",
        ):
            args["order"] = "asc"

        try:
            limit = int(args.get("limit", 15))
        except Exception:
            limit = 15

        limit = max(1, min(limit, 20))

        args["limit"] = limit

    result["arguments"] = args

    print("Planner:", result)

    return result