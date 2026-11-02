# -*- coding: utf-8 -*-
"""按官方文书样式重写 configs/document_templates.json"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "configs" / "document_templates.json"
ALL = ["user", "lawyer", "judge", "prosecutor"]


def F(key, label, typ="text", required=False, placeholder=""):
    d = {"key": key, "label": label, "type": typ, "required": required}
    if placeholder:
        d["placeholder"] = placeholder
    return d


def main() -> None:
    catalog: dict = {
        "version": 4,
        "watermark": "AI 生成草稿，须人工审核",
        "disclaimer": (
            "本文件由 AI 根据用户填写内容套用官方文书样式结构生成，仅供起草参考，"
            "不构成正式法律文书或律师意见。起诉状/答辩状/授权委托书结构参考最高人民"
            "法院《民事诉讼文书样式》；劳动仲裁申请书参考各地人社部门公开样式；离婚"
            "协议参考民政部门参考样板；律师函参考地方律师协会业务指引；裁判/检察文书"
            "参考最高法/最高检法律文书格式样本。使用前请由执业律师或办案人员根据个案"
            "修改并签名盖章。"
        ),
        "templates": [],
    }
    t = catalog["templates"]

    t.append(
        {
            "id": "civil_complaint",
            "name": "民事起诉状",
            "category": "诉讼文书",
            "description": "结构依据最高人民法院《民事起诉状（公民提起民事诉讼用）》样式。",
            "fields": [
                F("court", "受诉法院", required=True, placeholder="某某区人民法院"),
                F("plaintiff_name", "原告姓名", required=True),
                F("plaintiff_gender", "原告性别", placeholder="男/女"),
                F("plaintiff_birth", "原告出生日期", placeholder="××××年××月××日"),
                F("plaintiff_nation", "原告民族", placeholder="汉族"),
                F("plaintiff_job", "原告工作单位和职务或职业"),
                F("plaintiff_id", "原告身份证号"),
                F("plaintiff_address", "原告住所地", required=True, placeholder="住……（尽量写到门牌号）"),
                F("plaintiff_phone", "原告联系方式", required=True, placeholder="11位手机号"),
                F("agent", "委托诉讼代理人（如有）", placeholder="姓名，××律师事务所律师"),
                F("defendant_name", "被告姓名/名称", required=True),
                F("defendant_gender", "被告性别（自然人）"),
                F("defendant_job", "被告工作单位/职务（自然人）"),
                F("defendant_address", "被告住所地", required=True),
                F("defendant_phone", "被告联系方式（如知悉）", placeholder="11位手机号"),
                F(
                    "claims",
                    "诉讼请求",
                    "textarea",
                    True,
                    "分项列明，须具体可执行。例：一、……；二、本案诉讼费用由被告负担。",
                ),
                F(
                    "facts",
                    "事实和理由",
                    "textarea",
                    True,
                    "先写纠纷经过（时间地点人物起因经过结果），再写法律依据。",
                ),
                F("evidence", "证据和证据来源，证人姓名和住所", "textarea", False, "1.……；2.……"),
                F("copies", "起诉状副本份数", placeholder="按被告人数，如：1"),
                F("date", "落款日期", placeholder="××××年××月××日"),
            ],
            "body": (
                "# 民事起诉状\n\n> {{watermark}}\n\n"
                "**原告**：{{plaintiff_name}}，{{plaintiff_gender}}，{{plaintiff_birth}}生，"
                "{{plaintiff_nation}}，{{plaintiff_job}}，住{{plaintiff_address}}。"
                "身份证号：{{plaintiff_id}}。联系方式：{{plaintiff_phone}}。\n\n"
                "**委托诉讼代理人**：{{agent}}\n\n"
                "**被告**：{{defendant_name}}，{{defendant_gender}}，{{defendant_job}}，"
                "住{{defendant_address}}。联系方式：{{defendant_phone}}。\n\n"
                "**诉讼请求：**\n\n{{claims}}\n\n"
                "**事实和理由：**\n\n{{facts}}\n\n"
                "**证据和证据来源，证人姓名和住所：**\n\n{{evidence}}\n\n"
                "此致  \n**{{court}}**\n\n"
                "附：本起诉状副本{{copies}}份\n\n"
                "起诉人（签名）：{{plaintiff_name}}  \n{{date}}\n\n---\n{{disclaimer}}\n"
            ),
            "audiences": ALL,
        }
    )

    t.append(
        {
            "id": "civil_defense",
            "name": "民事答辩状",
            "category": "诉讼文书",
            "description": "结构依据最高人民法院《民事答辩状（公民对民事起诉提出答辩用）》样式。",
            "fields": [
                F("court", "受诉法院", required=True),
                F("case_no", "案号", placeholder="（××××）……民初……号"),
                F("cause", "案由", placeholder="如：民间借贷纠纷"),
                F("opponent_name", "对方当事人（原告）", required=True),
                F("respondent_name", "答辩人姓名/名称", required=True),
                F("respondent_gender", "答辩人性别（自然人）"),
                F("respondent_birth", "答辩人出生日期"),
                F("respondent_nation", "答辩人民族"),
                F("respondent_job", "答辩人工作单位和职务或职业"),
                F("respondent_address", "答辩人住所地", required=True),
                F("respondent_phone", "答辩人联系方式", placeholder="11位手机号"),
                F("agent", "委托诉讼代理人（如有）"),
                F("defense_points", "答辩意见", "textarea", True, "对诉讼请求的意见及事实理由"),
                F("evidence", "证据和证据来源，证人姓名和住所", "textarea"),
                F("copies", "答辩状副本份数", placeholder="1"),
                F("date", "落款日期"),
            ],
            "body": (
                "# 民事答辩状\n\n> {{watermark}}\n\n"
                "**答辩人**：{{respondent_name}}，{{respondent_gender}}，{{respondent_birth}}生，"
                "{{respondent_nation}}，{{respondent_job}}，住{{respondent_address}}。"
                "联系方式：{{respondent_phone}}。\n\n"
                "**委托诉讼代理人**：{{agent}}\n\n"
                "对**{{court}}**{{case_no}}{{opponent_name}}诉答辩人{{cause}}一案的起诉，答辩如下：\n\n"
                "{{defense_points}}\n\n"
                "**证据和证据来源，证人姓名和住所：**\n\n{{evidence}}\n\n"
                "此致  \n**{{court}}**\n\n"
                "附：本答辩状副本{{copies}}份\n\n"
                "答辩人（签名）：{{respondent_name}}  \n{{date}}\n\n---\n{{disclaimer}}\n"
            ),
            "audiences": ALL,
        }
    )

    t.append(
        {
            "id": "labor_arbitration",
            "name": "劳动人事争议仲裁申请书",
            "category": "劳动争议",
            "description": "结构参考各地人社部门公开的《劳动人事争议仲裁申请书》样式。",
            "fields": [
                F("commission", "仲裁委员会", required=True, placeholder="某某市劳动人事争议仲裁委员会"),
                F("applicant_name", "申请人姓名", required=True),
                F("applicant_gender", "申请人性别"),
                F("applicant_birth", "申请人出生日期"),
                F("applicant_nation", "申请人民族"),
                F("applicant_id", "申请人身份证号"),
                F("applicant_hukou", "户籍所在地"),
                F("applicant_address", "现住址/有效通讯地址", required=True),
                F("applicant_phone", "联系电话", placeholder="11位手机号"),
                F("respondent_name", "被申请人（单位）名称", required=True),
                F("respondent_credit", "统一社会信用代码"),
                F("respondent_address", "被申请人住所地", required=True),
                F("respondent_legal", "法定代表人/主要负责人及职务"),
                F("respondent_phone", "被申请人联系电话"),
                F("hire_date", "入职时间"),
                F("position", "岗位/工种"),
                F("claims", "仲裁请求", "textarea", True, "分项列明，金额与期间须具体明确"),
                F("facts", "事实和理由", "textarea", True, "劳动关系建立、争议经过、法律依据"),
                F("evidence", "证据和证据来源、证人姓名和住所", "textarea"),
                F("copies", "申请书副本份数", placeholder="按被申请人人数"),
                F("date", "落款日期"),
            ],
            "body": (
                "# 劳动人事争议仲裁申请书\n\n> {{watermark}}\n\n"
                "**申请人**：{{applicant_name}}，{{applicant_gender}}，{{applicant_birth}}生，"
                "{{applicant_nation}}，身份证号码：{{applicant_id}}，户籍所在地：{{applicant_hukou}}，"
                "现住址（有效通讯地址）：{{applicant_address}}，联系电话：{{applicant_phone}}。\n\n"
                "**被申请人**：{{respondent_name}}，统一社会信用代码：{{respondent_credit}}，"
                "住所地：{{respondent_address}}，法定代表人（主要负责人）：{{respondent_legal}}，"
                "联系电话：{{respondent_phone}}。\n\n"
                "入职时间：{{hire_date}}　岗位/工种：{{position}}\n\n"
                "**仲裁请求：**\n\n{{claims}}\n\n"
                "**事实和理由：**\n\n{{facts}}\n\n"
                "**证据和证据来源，证人姓名和住所：**\n\n{{evidence}}\n\n"
                "此致  \n**{{commission}}**\n\n"
                "申请人（签名捺印）：{{applicant_name}}  \n{{date}}\n\n"
                "附：本申请书副本{{copies}}份。\n\n---\n{{disclaimer}}\n"
            ),
            "audiences": ALL,
        }
    )

    t.append(
        {
            "id": "divorce_agreement",
            "name": "离婚协议书",
            "category": "婚姻家事",
            "description": "结构参考民政部门《离婚协议书》参考样板（自愿离婚、子女、财产、债务）。",
            "fields": [
                F("party_a", "男方姓名", required=True),
                F("party_a_id", "男方身份证件号码", required=True),
                F("party_a_address", "男方住址"),
                F("party_b", "女方姓名", required=True),
                F("party_b_id", "女方身份证件号码", required=True),
                F("party_b_address", "女方住址"),
                F("marriage_date", "结婚登记日期", required=True, placeholder="××××年××月××日"),
                F("registry", "结婚登记机关", placeholder="某某民政局"),
                F("reason", "离婚原因", placeholder="如：感情破裂、性格不合"),
                F(
                    "children",
                    "子女抚养、探视及抚养费约定",
                    "textarea",
                    True,
                    "无共同子女须写明「双方无共同子女」",
                ),
                F(
                    "property",
                    "夫妻共同财产处理",
                    "textarea",
                    True,
                    "房产写明地址；无财产写明「双方无共同财产」",
                ),
                F("debts", "债权债务处理", "textarea", True, "无共同债权债务须写明"),
                F("other", "其他约定", "textarea"),
                F("date", "签署日期"),
            ],
            "body": (
                "# 离婚协议书\n\n> {{watermark}}\n\n"
                "**男方**：{{party_a}}，身份证件号码：{{party_a_id}}，住址：{{party_a_address}}。\n\n"
                "**女方**：{{party_b}}，身份证件号码：{{party_b_id}}，住址：{{party_b_address}}。\n\n"
                "我们双方于{{marriage_date}}在{{registry}}登记结婚。婚后因{{reason}}，"
                "经双方协议达成离婚意愿，并对子女、财产、债务等事项协商一致，协议如下：\n\n"
                "**一、自愿离婚**\n\n{{party_a}}与{{party_b}}自愿离婚。\n\n"
                "**二、子女抚养安排**\n\n{{children}}\n\n"
                "**三、夫妻共同财产处理**\n\n{{property}}\n\n"
                "**四、债权债务处理**\n\n{{debts}}\n\n"
                "**五、其他约定**\n\n{{other}}\n\n"
                "**六、效力与份数**\n\n"
                "1. 本协议书为双方自愿签订，对男女双方均有法律约束力，违约方应负法律责任。  \n"
                "2. 本协议自双方取得《离婚证》之日起生效。  \n"
                "3. 本协议一式三份，男女双方各持一份，婚姻登记机关存档一份。\n\n"
                "我们自愿离婚，双方均具有完全民事行为能力，完全同意本协议书的各项安排，亦无其它不同意见。\n\n"
                "男方（签名）：____________　　女方（签名）：____________  \n"
                "日期：{{date}}　　　　　　　　日期：{{date}}\n\n---\n{{disclaimer}}\n"
            ),
            "audiences": ALL,
        }
    )

    t.append(
        {
            "id": "lease_supplement",
            "name": "房屋租赁合同补充协议",
            "category": "房屋租赁",
            "description": "常用房屋租赁合同补充/变更协议结构（当事人、鉴于条款、变更内容、效力）。",
            "fields": [
                F("landlord", "出租人（甲方）", required=True),
                F("landlord_id", "甲方证件号/信用代码"),
                F("tenant", "承租人（乙方）", required=True),
                F("tenant_id", "乙方证件号"),
                F("original_contract", "原合同名称及签订日期/编号", required=True),
                F("address", "租赁房屋坐落", required=True),
                F("changes", "补充/变更条款", "textarea", True, "分条写明租金、租期、押金、维修等变更"),
                F("effective_date", "本补充协议生效日"),
                F("date", "签署日期"),
            ],
            "body": (
                "# 房屋租赁合同补充协议\n\n> {{watermark}}\n\n"
                "**甲方（出租人）**：{{landlord}}（证件号/信用代码：{{landlord_id}}）  \n"
                "**乙方（承租人）**：{{tenant}}（证件号：{{tenant_id}}）\n\n"
                "**鉴于：**\n\n"
                "甲、乙双方于{{original_contract}}就坐落于**{{address}}**的房屋签订《房屋租赁合同》"
                "（下称「原合同」）。现双方经协商一致，就原合同未尽事宜或变更事项订立本补充协议，"
                "以资共同遵守。\n\n"
                "**第一条　补充/变更内容**\n\n{{changes}}\n\n"
                "**第二条　效力**\n\n"
                "1. 本补充协议是原合同的组成部分，与原合同具有同等法律效力。  \n"
                "2. 本补充协议与原合同约定不一致的，以本补充协议为准；本补充协议未约定的，仍按原合同执行。  \n"
                "3. 本补充协议自{{effective_date}}起生效（未填写则以双方签字/盖章之日为准）。  \n"
                "4. 本协议一式贰份，甲乙双方各执壹份，具有同等法律效力。\n\n"
                "甲方（签字/盖章）：____________　　乙方（签字/盖章）：____________  \n"
                "日期：{{date}}　　　　　　　　　　日期：{{date}}\n\n---\n{{disclaimer}}\n"
            ),
            "audiences": ALL,
        }
    )

    t.append(
        {
            "id": "consumer_complaint",
            "name": "消费投诉书",
            "category": "消费维权",
            "description": "结构依据中消协《受理消费者投诉工作导则》对投诉材料要素的要求。",
            "fields": [
                F("recipient", "受理单位", required=True, placeholder="某某消费者协会 / 市场监督管理局"),
                F("complainant", "投诉人姓名", required=True),
                F("complainant_id", "投诉人身份证号"),
                F("phone", "联系电话", required=True, placeholder="11位手机号"),
                F("address", "联系地址/邮编", required=True),
                F("merchant", "被投诉经营者名称", required=True),
                F("merchant_address", "被投诉人地址"),
                F("merchant_contact", "被投诉人联系人及电话"),
                F(
                    "purchase_info",
                    "购买/接受服务的时间、地点、品名、规格、数量、价格",
                    "textarea",
                    True,
                ),
                F("problem", "损害事实、争议过程及与经营者协商情况", "textarea", True),
                F("demands", "明确、具体的投诉请求", "textarea", True, "修理/更换/退货/退款/赔偿等"),
                F("evidence", "证据清单", "textarea", False, "发票、订单、聊天记录等"),
                F("date", "落款日期"),
            ],
            "body": (
                "# 投诉书\n\n> {{watermark}}\n\n"
                "**投诉人**：{{complainant}}，身份证号码：{{complainant_id}}，"
                "联系地址：{{address}}，联系电话：{{phone}}。\n\n"
                "**被投诉人**：{{merchant}}，地址：{{merchant_address}}，"
                "联系人及电话：{{merchant_contact}}。\n\n"
                "**一、消费基本情况**\n\n{{purchase_info}}\n\n"
                "**二、事实与理由**\n\n{{problem}}\n\n"
                "**三、投诉请求**\n\n{{demands}}\n\n"
                "**四、证据材料**\n\n{{evidence}}\n\n"
                "此致  \n**{{recipient}}**\n\n"
                "投诉人（签名）：{{complainant}}  \n{{date}}\n\n---\n{{disclaimer}}\n"
            ),
            "audiences": ALL,
        }
    )

    t.append(
        {
            "id": "lawyer_letter",
            "name": "律师函",
            "category": "律师文书",
            "description": "结构参考地方律师协会《律师函》业务指引（函号、委托声明、事实、法律分析、要求与期限）。",
            "fields": [
                F("doc_no", "函号", placeholder="（××××）××律函字第××号"),
                F("addressee", "收函方", required=True),
                F("client_name", "委托人", required=True),
                F("law_firm", "律师事务所", required=True, placeholder="某某律师事务所"),
                F("lawyer_name", "承办律师", required=True),
                F("matter", "事由摘要", placeholder="如：拖欠货款事宜"),
                F("facts", "委托人陈述的基本事实", "textarea", True),
                F("legal_basis", "法律分析及法律后果", "textarea", True),
                F(
                    "demands",
                    "解决问题的方法及建议（要求与期限）",
                    "textarea",
                    True,
                    "请于收函后×日内……",
                ),
                F("lawyer_phone", "律师联系方式"),
                F("date", "发函日期"),
            ],
            "body": (
                "# 律师函\n\n> {{watermark}}\n\n{{doc_no}}\n\n**{{addressee}}：**\n\n"
                "{{law_firm}}（以下简称「本所」）系依法设立的律师事务所。"
                "本所受**{{client_name}}**（以下简称「委托人」）委托，指派本所**{{lawyer_name}}**律师"
                "就贵方与委托人之间**{{matter}}**一事，依据相关法律法规规定，特致函如下：\n\n"
                "**一、委托人陈述的基本事实**\n\n{{facts}}\n\n"
                "以上事实系根据委托人向本所提供的陈述及材料整理。\n\n"
                "**二、法律分析及法律后果**\n\n{{legal_basis}}\n\n"
                "**三、解决问题的方法及建议**\n\n"
                "为妥善解决上述纠纷、避免诉累，本律师建议：\n\n{{demands}}\n\n"
                "如贵方既不及时回复，也不按上述方案履行，可能导致双方分歧加深，委托人将依法通过"
                "协商、调解、仲裁或诉讼等途径维护自身合法权益，并保留向贵方主张因此产生的合理费用"
                "的权利。请贵方慎重考虑。\n\n"
                "本律师函所依据的事实及证据系由委托人提供，且委托人已对其真实性、完整性、准确性负责；"
                "并不排除贵方与委托人对客观事实的认知有所出入。贵方如对本函涉及事实有异议，或对问题"
                "解决有其他合理建议，请直接与本律师联系。\n\n"
                "本律师函不得以任何方式被解释为委托人对权利作任何放弃、对义务作任何增加。\n\n"
                "特此函告。\n\n律师联系方式：{{lawyer_phone}}\n\n"
                "**{{law_firm}}**（盖章）  \n律师：{{lawyer_name}}（签名）  \n{{date}}\n\n"
                "---\n{{disclaimer}}  \n"
                "**特别提示**：正式律师函须由执业律师审核署名并由律师事务所盖章后发出。\n"
            ),
            "audiences": ["lawyer", "user"],
        }
    )

    t.append(
        {
            "id": "power_of_attorney",
            "name": "授权委托书",
            "category": "通用文书",
            "description": "结构依据最高人民法院《授权委托书（公民委托诉讼代理人用）》样式。",
            "fields": [
                F("principal", "委托人", required=True),
                F("principal_gender", "委托人性别"),
                F("principal_birth", "委托人出生日期"),
                F("principal_nation", "委托人民族"),
                F("principal_job", "委托人工作单位和职务或职业"),
                F("principal_address", "委托人住所地", required=True),
                F("principal_phone", "委托人联系方式", placeholder="11位手机号"),
                F("principal_id", "委托人身份证号"),
                F("agent", "受委托人", required=True),
                F("agent_firm", "受委托人单位", placeholder="××律师事务所律师 / 或写明与委托人关系"),
                F("agent_phone", "受委托人联系方式"),
                F("case_info", "案件当事人及案由", required=True, placeholder="在……一案中"),
                F(
                    "powers",
                    "委托事项与权限",
                    "textarea",
                    True,
                    "一般授权或特别授权（承认、放弃、变更诉讼请求，和解，反诉，上诉等须特别授权）",
                ),
                F("date", "签署日期"),
            ],
            "body": (
                "# 授权委托书\n\n> {{watermark}}\n\n"
                "**委托人**：{{principal}}，{{principal_gender}}，{{principal_birth}}出生，"
                "{{principal_nation}}，{{principal_job}}，住{{principal_address}}。"
                "联系方式：{{principal_phone}}。身份证号：{{principal_id}}。\n\n"
                "**受委托人**：{{agent}}，{{agent_firm}}，联系方式：{{agent_phone}}。\n\n"
                "现委托{{agent}}在**{{case_info}}**中，作为我方参加诉讼的委托诉讼代理人。\n\n"
                "**委托事项与权限如下：**\n\n{{powers}}\n\n"
                "（说明：代为承认、放弃、变更诉讼请求，进行和解，提起反诉或者上诉，必须有委托人的特别授权。）\n\n"
                "委托人（签名）：____________  \n{{date}}\n\n---\n{{disclaimer}}\n"
            ),
            "audiences": ["lawyer", "user"],
        }
    )

    t.append(
        {
            "id": "judgment_outline",
            "name": "民事判决书（结构草稿）",
            "category": "审判文书",
            "description": "结构依据最高人民法院《民事判决书（第一审普通程序用）》样式，供整理说理（非正式文书）。",
            "audiences": ["judge"],
            "fields": [
                F("court", "法院名称", required=True),
                F("case_no", "案号", required=True, placeholder="（××××）……民初……号"),
                F("parties", "当事人及其他诉讼参加人基本情况", "textarea", True),
                F(
                    "procedure",
                    "案件由来和审理经过",
                    "textarea",
                    True,
                    "立案日期、程序、开庭方式、到庭人员等",
                ),
                F("claims", "原告诉称（诉讼请求及事实理由）", "textarea", True),
                F("defense", "被告辩称", "textarea", True),
                F("third_party", "第三人诉/述称（如有）", "textarea"),
                F("facts", "本院认定的证据和事实", "textarea", True),
                F("issues", "争议焦点", "textarea"),
                F("reasoning", "本院认为", "textarea", True),
                F("laws", "裁判依据（法条）", "textarea", True, "依照《……法》第×条……规定"),
                F("judgment", "判决主文", "textarea", True, "分项写明"),
                F("fee", "案件受理费负担"),
                F("appeal_court", "上诉法院", placeholder="某某中级人民法院"),
                F("judges", "审判人员署名", placeholder="审判长……　审判员……"),
                F("date", "判决日期"),
                F("clerk", "书记员"),
            ],
            "body": (
                "# {{court}}\n\n# 民事判决书\n\n{{case_no}}\n\n> {{watermark}}\n\n"
                "{{parties}}\n\n{{procedure}}\n\n{{claims}}\n\n{{defense}}\n\n{{third_party}}\n\n"
                "当事人围绕诉讼请求依法提交了证据，本院组织当事人进行了证据交换和质证。"
                "对当事人无异议的证据，本院予以确认并在卷佐证。对有争议的证据和事实，本院认定如下：\n\n"
                "{{facts}}\n\n争议焦点：{{issues}}\n\n"
                "本院认为，{{reasoning}}\n\n"
                "综上所述，……。依照{{laws}}规定，判决如下：\n\n{{judgment}}\n\n"
                "如果未按本判决指定的期间履行给付金钱义务，应当依照《中华人民共和国民事诉讼法》"
                "相关规定，加倍支付迟延履行期间的债务利息。\n\n"
                "案件受理费{{fee}}。\n\n"
                "如不服本判决，可以在判决书送达之日起十五日内，向本院递交上诉状，并按照对方当事人"
                "或者代表人的人数提出副本，上诉于**{{appeal_court}}**。\n\n"
                "{{judges}}  \n{{date}}  \n（院印）  \n书记员　{{clerk}}\n\n---\n{{disclaimer}}\n"
            ),
        }
    )

    t.append(
        {
            "id": "civil_ruling_outline",
            "name": "民事裁定书（结构草稿）",
            "category": "审判文书",
            "description": "参考最高人民法院民事裁定书通用结构（当事人、裁定事项、事实理由、裁定主文、救济告知）。",
            "audiences": ["judge"],
            "fields": [
                F("court", "法院名称", required=True),
                F("case_no", "案号", required=True),
                F("parties", "当事人基本情况", "textarea", True),
                F(
                    "matter",
                    "裁定所涉申请/事项",
                    required=True,
                    placeholder="如：准许撤诉 / 管辖权异议 / 财产保全",
                ),
                F("facts", "基本事实与审查情况", "textarea", True),
                F("reason", "本院认为（裁定理由）", "textarea", True),
                F("laws", "法律依据", "textarea", True),
                F("result", "裁定主文", "textarea", True),
                F("remedy", "救济告知", "textarea", False, "上诉/复议期限与受理法院"),
                F("judges", "审判人员"),
                F("date", "裁定日期"),
                F("clerk", "书记员"),
            ],
            "body": (
                "# {{court}}\n\n# 民事裁定书\n\n{{case_no}}\n\n> {{watermark}}\n\n"
                "{{parties}}\n\n本院在审理{{matter}}过程中，查明：\n\n{{facts}}\n\n"
                "本院认为，{{reason}}\n\n依照{{laws}}规定，裁定如下：\n\n{{result}}\n\n"
                "{{remedy}}\n\n{{judges}}  \n{{date}}  \n（院印）  \n书记员　{{clerk}}\n\n"
                "---\n{{disclaimer}}\n"
            ),
        }
    )

    t.append(
        {
            "id": "indictment_outline",
            "name": "起诉书（结构草稿）",
            "category": "检察文书",
            "description": "结构参考《人民检察院刑事诉讼法律文书格式样本》起诉书体例。",
            "audiences": ["prosecutor"],
            "fields": [
                F("procuratorate", "检察院名称", required=True),
                F("doc_no", "文号", placeholder="××检刑诉〔××××〕××号"),
                F(
                    "defendant",
                    "被告人基本情况",
                    "textarea",
                    True,
                    "姓名、性别、出生日期、身份证号、民族、文化程度、职业、住址、前科及强制措施等",
                ),
                F("source", "案由和案件的审查过程", "textarea", True, "侦查机关、移送时间、退查等情况"),
                F("facts", "经依法审查查明的犯罪事实", "textarea", True),
                F(
                    "evidence",
                    "认定上述事实的证据",
                    "textarea",
                    True,
                    "分种类列明：物证、书证、证人证言等",
                ),
                F("charge", "起诉罪名", required=True),
                F("law", "起诉的理由和根据", "textarea", True, "触犯刑法条款、应当追究刑事责任"),
                F("court", "受诉法院", required=True),
                F("date", "日期"),
            ],
            "body": (
                "# {{procuratorate}}\n\n# 起　诉　书\n\n{{doc_no}}\n\n> {{watermark}}\n\n"
                "**被告人**　{{defendant}}\n\n{{source}}\n\n经依法审查查明：\n\n{{facts}}\n\n"
                "认定上述事实的证据如下：\n\n{{evidence}}\n\n"
                "本院认为，被告人的行为触犯了{{law}}，犯罪事实清楚，证据确实、充分，"
                "应当以**{{charge}}**追究其刑事责任。根据《中华人民共和国刑事诉讼法》第一百七十六条"
                "的规定，提起公诉，请依法判处。\n\n此致  \n**{{court}}**\n\n"
                "检察员：____________  \n{{date}}  \n（院印）\n\n"
                "附：1. 被告人现在处所；2. 案卷材料和证据；3. 证人、鉴定人名单等。\n\n"
                "---\n{{disclaimer}}\n"
            ),
        }
    )

    t.append(
        {
            "id": "non_prosecution_outline",
            "name": "不起诉决定书（结构草稿）",
            "category": "检察文书",
            "description": "结构参考最高检不起诉决定书格式样本。",
            "audiences": ["prosecutor"],
            "fields": [
                F("procuratorate", "检察院名称", required=True),
                F("doc_no", "文号", placeholder="××检××刑不诉〔××××〕××号"),
                F("suspect", "被不起诉人基本情况", "textarea", True),
                F("defender", "辩护人（如有）"),
                F("source", "案由和案件来源", "textarea", True),
                F(
                    "type",
                    "不起诉类型",
                    required=True,
                    placeholder="法定不起诉 / 酌定不起诉 / 证据不足不起诉",
                ),
                F("facts", "经本院依法审查查明", "textarea", True),
                F("reason", "本院认为（不起诉理由）", "textarea", True),
                F(
                    "law",
                    "法律依据",
                    "textarea",
                    True,
                    "依照《刑事诉讼法》……规定，决定不起诉",
                ),
                F("property", "涉案财物处理情况", "textarea"),
                F("notice", "告知事项", "textarea", False, "申诉/自诉权利告知"),
                F("date", "日期"),
            ],
            "body": (
                "# {{procuratorate}}\n\n# 不起诉决定书\n\n{{doc_no}}\n\n> {{watermark}}\n\n"
                "**被不起诉人**　{{suspect}}\n\n**辩护人**　{{defender}}\n\n{{source}}\n\n"
                "不起诉类型：{{type}}\n\n经本院依法审查查明：\n\n{{facts}}\n\n"
                "本院认为，{{reason}}\n\n依照{{law}}，决定对被不起诉人不起诉。\n\n"
                "{{property}}\n\n{{notice}}\n\n"
                "被害人如果不服本决定，可以自收到本决定书后七日以内向上一级人民检察院申诉，"
                "请求提起公诉；也可以不经申诉，直接向人民法院提起自诉。\n\n"
                "**{{procuratorate}}**  \n{{date}}  \n（院印）\n\n---\n{{disclaimer}}\n"
            ),
        }
    )

    t.append(
        {
            "id": "sentencing_suggest",
            "name": "量刑建议书（结构草稿）",
            "category": "检察文书",
            "description": "参考检察机关量刑建议文书常用结构（被告人、指控罪名、量刑情节、建议幅度）。",
            "audiences": ["prosecutor"],
            "fields": [
                F("procuratorate", "检察院名称", required=True),
                F("doc_no", "文号"),
                F("defendant", "被告人", required=True),
                F("charge", "指控罪名", required=True),
                F("baseline", "量刑起点与基准刑考量", "textarea", True),
                F("aggravating", "从重处罚情节", "textarea"),
                F("mitigating", "从轻、减轻处罚情节", "textarea"),
                F("suggest", "量刑建议（主刑、附加刑、执行方式等）", "textarea", True),
                F("law", "法律依据", "textarea"),
                F("date", "日期"),
            ],
            "body": (
                "# {{procuratorate}}\n\n# 量刑建议书\n\n{{doc_no}}\n\n> {{watermark}}\n\n"
                "被告人：{{defendant}}  \n指控罪名：{{charge}}\n\n"
                "**一、量刑事实与情节**\n\n（一）量刑起点与基准刑考量\n\n{{baseline}}\n\n"
                "（二）从重处罚情节\n\n{{aggravating}}\n\n"
                "（三）从轻、减轻处罚情节\n\n{{mitigating}}\n\n"
                "**二、法律依据**\n\n{{law}}\n\n"
                "**三、量刑建议**\n\n综合全案事实、情节，建议对被告人{{defendant}}处以：\n\n"
                "{{suggest}}\n\n请法庭依法采纳。\n\n"
                "检察员：____________  \n{{date}}  \n（院印）\n\n---\n{{disclaimer}}\n"
            ),
        }
    )

    t.append(
        {
            "id": "lawyer_opinion_brief",
            "name": "案件分析备忘录",
            "category": "律师文书",
            "description": "律师内部办案分析备忘常用结构（事实、请求权基础、争点、证据、风险、策略）。",
            "audiences": ["lawyer"],
            "fields": [
                F("client", "委托人", required=True),
                F("opponent", "相对方"),
                F("matter", "案由/事项", required=True),
                F("facts", "基本事实摘要", "textarea", True),
                F("claims_basis", "请求权基础/抗辩路径", "textarea", True),
                F("issues", "主要争点", "textarea", True),
                F("evidence", "证据状况与补强方向", "textarea", True),
                F("risks", "风险点与不利后果", "textarea", True),
                F("plan", "下一步工作安排", "textarea", True),
                F("author", "拟稿人"),
                F("date", "日期"),
            ],
            "body": (
                "# 案件分析备忘录\n\n> {{watermark}}\n\n"
                "**委托人**：{{client}}  \n**相对方**：{{opponent}}  \n"
                "**案由/事项**：{{matter}}  \n**拟稿人**：{{author}}　**日期**：{{date}}\n\n"
                "**一、基本事实**\n\n{{facts}}\n\n"
                "**二、请求权基础 / 抗辩路径**\n\n{{claims_basis}}\n\n"
                "**三、主要争点**\n\n{{issues}}\n\n"
                "**四、证据状况与补强**\n\n{{evidence}}\n\n"
                "**五、风险提示**\n\n{{risks}}\n\n"
                "**六、下一步工作**\n\n{{plan}}\n\n"
                "---\n{{disclaimer}}  \n（本稿为律师内部工作备忘，非正式法律意见书。）\n"
            ),
        }
    )

    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} templates={len(t)} version={catalog['version']}")


if __name__ == "__main__":
    main()
