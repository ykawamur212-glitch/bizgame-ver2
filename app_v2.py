import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import firebase_admin
from firebase_admin import credentials, firestore
import os

st.set_page_config(page_title="BizGame Ver.2 シミュレーター", layout="wide")

# =============================================================================
# ▼ Firebase初期化 (ローカル/クラウド両対応)
# =============================================================================
if not firebase_admin._apps:
    if os.path.exists("firebase_key.json"):
        # ローカル環境（PC）の場合
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    else:
        # クラウド環境（Streamlit Cloud）の場合
        try:
            firebase_secrets = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_secrets)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error("【クラウド認証エラー】Streamlitの「Secrets」にFirebaseの鍵情報が設定されていないか、形式が間違っています。")
            st.error(f"詳細: {e}")
            st.stop()

db = firestore.client()

def get_market_state():
    doc = db.collection('market_state').document('current').get()
    return doc.to_dict() if doc.exists else None

def get_team_data(team_name):
    doc = db.collection('teams').document(team_name).get()
    return doc.to_dict() if doc.exists else None

def get_all_teams():
    docs = db.collection('teams').stream()
    all_teams = {doc.id: doc.to_dict() for doc in docs}
    valid_teams = ["Team A", "Team B", "Team C", "Team D", "Team E"]
    return {k: v for k, v in all_teams.items() if k in valid_teams}

market = get_market_state()
if not market:
    st.error("データベースが初期化されていません。ローカル環境で init_v2.py から初期化を行ってください。")
    st.stop()

st.sidebar.title("ログイン")
user_role = st.sidebar.radio("モード選択", ["プレイヤー (各チーム)", "ゲーム管理者"])

# =============================================================================
# ▼ プレイヤーモード
# =============================================================================
if user_role == "プレイヤー (各チーム)":
    teams_list = ["Team A", "Team B", "Team C", "Team D", "Team E"]
    selected_team = st.sidebar.selectbox("担当チームを選択", teams_list)
    
    team_data = get_team_data(selected_team)
    entered_pin = st.sidebar.text_input("チームPIN (4桁)", type="password")
    
    if entered_pin != team_data.get('pin', ''):
        st.warning("正しいチームPINを入力してください。")
        st.stop()
    
    st.title(f"🏢 {selected_team} - 第 {market['turn']} 期 経営ダッシュボード")

    if not team_data.get('decision_submitted', False):
        st.info("今期の意思決定を入力し、「提出」を押してください。")
        with st.form(f"decision_form_{selected_team}"):
            st.subheader("💰 財務・借入")
            em_debt_now = team_data.get('emergency_debt', 0)
            if em_debt_now > 0:
                st.error(f"⚠️ 警告: 緊急借入金（年利20%）が ¥{em_debt_now:,.0f} あります。新規借入欄にマイナスの数字を入れると優先して返済されます。")
                
            borrowing = st.number_input("新規借入額 (返済する場合はマイナス入力)", value=0, step=10000)
            
            c_gen, c_adv = st.columns(2)
            
            with c_gen:
                st.markdown("### 📦 汎用品 (Generic) 部門")
                st.caption("価格競争が激しく、大量生産が鍵となる市場。")
                gen_invest = st.number_input("[汎用] 設備投資額", min_value=0, value=0, step=1000)
                gen_mat = st.number_input("[汎用] 材料発注数", min_value=0, value=0, step=100)
                gen_hire = st.number_input("[汎用] 新規採用人数", min_value=0, value=0, step=1)
                gen_fire = st.number_input("[汎用] 解雇人数", min_value=0, max_value=team_data.get('gen_engineers', 0), value=0, step=1)
                gen_price = st.number_input("[汎用] 販売価格", min_value=1, value=20, step=1)
                gen_sga = st.number_input("[汎用] 営業費", min_value=0, value=1000, step=500)

            with c_adv:
                st.markdown("### 🚀 先端品 (Advanced) 部門")
                st.caption("高単価・高利益だが、開発費(SGA)や設備投資が重い市場。")
                adv_invest = st.number_input("[先端] 設備投資額", min_value=0, value=0, step=1000)
                adv_mat = st.number_input("[先端] 材料発注数", min_value=0, value=0, step=100)
                adv_hire = st.number_input("[先端] 新規採用人数", min_value=0, value=0, step=1)
                adv_fire = st.number_input("[先端] 解雇人数", min_value=0, max_value=team_data.get('adv_engineers', 0), value=0, step=1)
                adv_price = st.number_input("[先端] 販売価格", min_value=1, value=80, step=1)
                adv_sga = st.number_input("[先端] 営業費", min_value=0, value=2000, step=500)

            if st.form_submit_button("意思決定を提出する"):
                db.collection('teams').document(selected_team).update({
                    'current_decision': {
                        'borrowing': borrowing,
                        'gen_invest': gen_invest, 'gen_mat': gen_mat, 'gen_hire': gen_hire, 'gen_fire': gen_fire, 'gen_price': gen_price, 'gen_sga': gen_sga,
                        'adv_invest': adv_invest, 'adv_mat': adv_mat, 'adv_hire': adv_hire, 'adv_fire': adv_fire, 'adv_price': adv_price, 'adv_sga': adv_sga
                    },
                    'decision_submitted': True
                })
                st.success("提出完了！画面を更新します...")
                st.rerun()
    else:
        st.success("✅ 今期の意思決定を提出済みです。管理者のターン実行をお待ちください。")
        if st.button("提出を取り消す（修正する）"):
             db.collection('teams').document(selected_team).update({'decision_submitted': False})
             st.rerun()

    if market['turn'] > 1:
        st.markdown("---")
        last_turn = str(market['turn'] - 1)
        history = team_data.get('history', {})
        
        if last_turn in history:
            res = history[last_turn]
            st.subheader(f"📊 第 {last_turn} 期 業績レポート")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("現預金残高", f"¥{team_data.get('cash', 0):,.0f}")
            m2.metric("利益剰余金 (最終スコア)", f"¥{team_data.get('retained_earnings', 0):,.0f}")
            
            net_assets_current = team_data.get('capital', 0) + team_data.get('retained_earnings', 0)
            if net_assets_current < 0:
                eq_ratio_str = "0.0% (債務超過)"
            else:
                eq_ratio_str = f"{res.get('equity_ratio', 0):.1f}%"
                
            m3.metric("自己資本比率", eq_ratio_str)
            m4.metric("適用金利", f"{res.get('interest_rate', 0) * 100:.1f}%")

            tab_fs, tab_chart, tab_comp = st.tabs(["📑 財務諸表 (B/S & P/L)", "📈 利益剰余金 推移", "🕵️ 競合分析 (前期)"])
            
            with tab_fs:
                col_pl, col_bs = st.columns(2)
                with col_pl:
                    st.markdown("**損益計算書 (P/L)**")
                    pl_data = {
                        "科目": ["売上高", "売上原価", "売上総利益", "営業費 (SGA)", "営業利益", "支払利息", "在庫評価損", "税引前当期純利益", "法人税等 (40%)", "当期純利益"],
                        "金額": [
                            res.get('revenue', 0), res.get('cogs', 0), res.get('gross_profit', 0), res.get('sga', 0), 
                            res.get('op_profit', 0), res.get('interest_exp', 0), res.get('valuation_loss', 0), 
                            res.get('pre_tax_income', 0), res.get('tax', 0), res.get('net_income', 0)
                        ]
                    }
                    df_pl = pd.DataFrame(pl_data)
                    st.dataframe(df_pl.style.format({"金額": "¥{:,.0f}"}), use_container_width=True, hide_index=True)
                
                with col_bs:
                    st.markdown("**貸借対照表 (B/S)**")
                    em_debt = team_data.get('emergency_debt', 0)
                    normal_debt = team_data.get('debt', 0)
                    total_liabilities = normal_debt + em_debt
                    
                    bs_data = {
                        "科目": ["現預金", "材料在庫", "製品在庫", "設備(簿価)", "【資産合計】", "通常借入金", "緊急借入金 (20%)", "【負債合計】", "資本金", "利益剰余金", "【純資産合計】", "【負債・純資産合計】"],
                        "金額": [
                            team_data.get('cash', 0), 
                            team_data.get('gen_mat_inventory_value', 0) + team_data.get('adv_mat_inventory_value', 0),
                            team_data.get('gen_prod_inventory_value', 0) + team_data.get('adv_prod_inventory_value', 0),
                            res.get('total_equip_value', 0),
                            res.get('total_assets', 0),
                            normal_debt,
                            em_debt,
                            total_liabilities,
                            team_data.get('capital', 0),
                            team_data.get('retained_earnings', 0),
                            team_data.get('capital', 0) + team_data.get('retained_earnings', 0),
                            res.get('total_assets', 0)
                        ]
                    }
                    df_bs = pd.DataFrame(bs_data)
                    st.dataframe(df_bs.style.format({"金額": "¥{:,.0f}"}), use_container_width=True, hide_index=True)

            with tab_chart:
                re_history = []
                for t in range(1, market['turn']):
                    for t_name, t_all_data in get_all_teams().items():
                        hist = t_all_data.get('history', {})
                        t_str = str(t)
                        if t_str in hist:
                            re_history.append({'Turn': t, 'Team': t_name, 'Retained Earnings': hist[t_str].get('end_retained_earnings', 0)})
                
                if re_history:
                    df_chart = pd.DataFrame(re_history)
                    fig = px.line(df_chart, x='Turn', y='Retained Earnings', color='Team', markers=True, title='利益剰余金の推移 (最終順位スコア)')
                    fig.update_layout(yaxis_title="利益剰余金 (¥)", xaxis_title="期 (Turn)")
                    st.plotly_chart(fig, use_container_width=True)

            with tab_comp:
                st.markdown("**前期 (第{}期) の市場データ**".format(last_turn))
                comp_data = []
                for t_name, t_all_data in get_all_teams().items():
                    hist = t_all_data.get('history', {})
                    if last_turn in hist:
                        h = hist[last_turn]
                        comp_data.append({
                            "チーム": t_name,
                            "汎用 価格": h.get('gen_price', 0),
                            "先端 価格": h.get('adv_price', 0),
                            "売上高": h.get('revenue', 0),
                            "当期純利益": h.get('net_income', 0),
                            "総資産": h.get('total_assets', 0),
                            "自己資本比率(%)": h.get('equity_ratio', 0)
                        })
                
                df_comp = pd.DataFrame(comp_data)
                if not df_comp.empty:
                    st.dataframe(
                        df_comp.style.format({
                            "汎用 価格": "¥{:,.0f}",
                            "先端 価格": "¥{:,.0f}",
                            "売上高": "¥{:,.0f}",
                            "当期純利益": "¥{:,.0f}",
                            "総資産": "¥{:,.0f}",
                            "自己資本比率(%)": "{:.1f}%"
                        }), use_container_width=True, hide_index=True
                    )
                else:
                    st.info("表示できる競合データがありません。")

# =============================================================================
# ▼ 管理者モード
# =============================================================================
elif user_role == "ゲーム管理者":
    st.sidebar.markdown("---")
    admin_pass = st.sidebar.text_input("管理者パスワード", type="password")
    
    if admin_pass == "0234":
        st.title(f"👑 管理者ダッシュボード - 第 {market['turn']} 期")
        
        all_teams_data = get_all_teams()
        
        st.subheader("各チームの提出状況")
        status_cols = st.columns(len(all_teams_data))
        all_submitted = True
        
        for i, (t_name, t_data) in enumerate(sorted(all_teams_data.items())):
            submitted = t_data.get('decision_submitted', False)
            status_cols[i].metric(t_name, "提出済 ✅" if submitted else "未提出 ⏳")
            if not submitted: all_submitted = False
            
        if st.button("🔄 提出状況を最新に更新"):
            st.rerun()

        st.markdown("---")
        
        if market['turn'] > 1:
            last_t = str(market['turn'] - 1)
            st.subheader(f"📊 第 {last_t} 期 財務諸表一覧 (全チーム)")
            
            pl_data_list = []
            bs_data_list = []
            
            for t_name, t_data in sorted(all_teams_data.items()):
                hist = t_data.get('history', {})
                
                if last_t in hist:
                    h = hist[last_t]
                    pl_data_list.append({
                        "チーム": t_name,
                        "売上高": h.get('revenue', 0),
                        "売上原価": h.get('cogs', 0),
                        "売上総利益": h.get('gross_profit', 0),
                        "営業費": h.get('sga', 0),
                        "営業利益": h.get('op_profit', 0),
                        "支払利息": h.get('interest_exp', 0),
                        "在庫評価損": h.get('valuation_loss', 0),
                        "法人税等": h.get('tax', 0),
                        "当期純利益": h.get('net_income', 0)
                    })
                
                em_debt = t_data.get('emergency_debt', 0)
                normal_debt = t_data.get('debt', 0)
                mat_inv = t_data.get('gen_mat_inventory_value', 0) + t_data.get('adv_mat_inventory_value', 0)
                prod_inv = t_data.get('gen_prod_inventory_value', 0) + t_data.get('adv_prod_inventory_value', 0)
                equip_val = sum(eq['book_value'] for eq in t_data.get('gen_equipment_list', [])) + sum(eq['book_value'] for eq in t_data.get('adv_equipment_list', []))
                
                bs_data_list.append({
                    "チーム": t_name,
                    "現預金": t_data.get('cash', 0),
                    "在庫(合計)": mat_inv + prod_inv,
                    "設備(簿価)": equip_val,
                    "【資産合計】": t_data.get('cash', 0) + mat_inv + prod_inv + equip_val,
                    "通常借入金": normal_debt,
                    "緊急借入金": em_debt,
                    "資本金": t_data.get('capital', 0),
                    "利益剰余金": t_data.get('retained_earnings', 0),
                    "【純資産】": t_data.get('capital', 0) + t_data.get('retained_earnings', 0)
                })

            tab_admin_pl, tab_admin_bs = st.tabs(["📑 損益計算書 (P/L) 一覧", "💰 貸借対照表 (B/S) 一覧"])
            
            with tab_admin_pl:
                if pl_data_list:
                    df_admin_pl = pd.DataFrame(pl_data_list)
                    format_dict_pl = {col: "¥{:,.0f}" for col in df_admin_pl.columns if col != "チーム"}
                    st.dataframe(df_admin_pl.style.format(format_dict_pl), use_container_width=True, hide_index=True)
                else:
                    st.info("前期のデータがありません。")
                    
            with tab_admin_bs:
                if bs_data_list:
                    df_admin_bs = pd.DataFrame(bs_data_list)
                    format_dict_bs = {col: "¥{:,.0f}" for col in df_admin_bs.columns if col != "チーム"}
                    st.dataframe(df_admin_bs.style.format(format_dict_bs), use_container_width=True, hide_index=True)
                else:
                    st.info("B/Sデータがありません。")
            
            st.markdown("---")

        st.subheader("⚙️ 今期の市場環境（ボトルネック）設定")
        c_bot1, c_bot2 = st.columns(2)
        with c_bot1:
            gen_factor = st.slider("汎用品の生産効率 (1.0 = 100%)", 0.5, 1.5, market.get('gen_bottleneck_factor', 1.0), 0.1)
        with c_bot2:
            adv_factor = st.slider("先端品の生産効率 (1.0 = 100%)", 0.5, 1.5, market.get('adv_bottleneck_factor', 1.0), 0.1)
            
        if st.button("市場環境を保存"):
            db.collection('market_state').document('current').update({
                'gen_bottleneck_factor': gen_factor, 'adv_bottleneck_factor': adv_factor
            })
            st.success("保存しました。")
            st.rerun()

        st.markdown("---")
        
        if all_submitted:
            if st.button(f"🚀 第 {market['turn']} 期の決算処理を実行する", type="primary", use_container_width=True):
                
                batch = db.batch()
                
                for t_name, t_data in all_teams_data.items():
                    dec = t_data['current_decision']
                    borrowing_input = dec.get('borrowing', 0)
                    em_debt = t_data.get('emergency_debt', 0)
                    
                    if borrowing_input < 0:
                        repay_amount = -borrowing_input
                        pay_em = min(repay_amount, em_debt)
                        em_debt -= pay_em
                        repay_amount -= pay_em
                        pay_normal = min(repay_amount, t_data.get('debt', 0))
                        t_data['debt'] = t_data.get('debt', 0) - pay_normal
                    else:
                        t_data['debt'] = t_data.get('debt', 0) + borrowing_input
                        
                    t_data['emergency_debt'] = em_debt
                    t_data['cash'] += borrowing_input
                    
                    total_equip_val_gen = sum(eq['book_value'] for eq in t_data.get('gen_equipment_list', []))
                    total_equip_val_adv = sum(eq['book_value'] for eq in t_data.get('adv_equipment_list', []))
                    total_assets_beginning = (t_data['cash'] + t_data.get('gen_mat_inventory_value', 0) + t_data.get('gen_prod_inventory_value', 0) +
                                              t_data.get('adv_mat_inventory_value', 0) + t_data.get('adv_prod_inventory_value', 0) + 
                                              total_equip_val_gen + total_equip_val_adv)
                    
                    net_assets = t_data.get('capital', 0) + t_data.get('retained_earnings', 0)
                    
                    if net_assets < 0:
                        equity_ratio = 0.0 
                        interest_rate = market['base_interest_rate'] + 0.15 
                    else:
                        equity_ratio = (net_assets / total_assets_beginning * 100) if total_assets_beginning > 0 else 0
                        interest_rate = market['base_interest_rate']
                        if equity_ratio < 10: interest_rate += 0.10
                        elif equity_ratio < 30: interest_rate += 0.05
                        
                    interest_exp = (t_data.get('debt', 0) * interest_rate) + (em_debt * 0.20)
                    
                    t_data['gen_engineers'] = t_data.get('gen_engineers', 0) + (dec.get('gen_hire', 0) - dec.get('gen_fire', 0))
                    if dec.get('gen_invest', 0) > 0:
                        t_data['gen_equipment_list'].append({'initial_cost': dec['gen_invest'], 'book_value': dec['gen_invest']})
                    
                    t_data['adv_engineers'] = t_data.get('adv_engineers', 0) + (dec.get('adv_hire', 0) - dec.get('adv_fire', 0))
                    if dec.get('adv_invest', 0) > 0:
                        t_data['adv_equipment_list'].append({'initial_cost': dec['adv_invest'], 'book_value': dec['adv_invest']})
                        
                    gen_dep_exp, current_gen_equip_val = 0, 0
                    for eq in t_data.get('gen_equipment_list', []):
                        if eq['book_value'] > 0:
                            dep = min(eq['initial_cost'] * 0.2, eq['book_value'])
                            eq['book_value'] -= dep; gen_dep_exp += dep
                        current_gen_equip_val += eq['book_value']
                        
                    adv_dep_exp, current_adv_equip_val = 0, 0
                    for eq in t_data.get('adv_equipment_list', []):
                        if eq['book_value'] > 0:
                            dep = min(eq['initial_cost'] * 0.2, eq['book_value'])
                            eq['book_value'] -= dep; adv_dep_exp += dep
                        current_adv_equip_val += eq['book_value']
                        
                    total_equip_val = current_gen_equip_val + current_adv_equip_val
                    
                    gen_mat_cost = dec.get('gen_mat', 0) * market['gen_mat_price']
                    t_data['gen_mat_inventory_qty'] = t_data.get('gen_mat_inventory_qty', 0) + dec.get('gen_mat', 0)
                    t_data['gen_mat_inventory_value'] = t_data.get('gen_mat_inventory_value', 0) + gen_mat_cost
                    gen_labor_cost = (t_data['gen_engineers'] * market['gen_base_salary']) + (dec.get('gen_hire', 0) * market['gen_hiring_cost']) + (dec.get('gen_fire', 0) * market['gen_firing_cost'])
                    
                    cap_eq_gen = current_gen_equip_val * 2 * market['gen_bottleneck_factor']
                    cap_hr_gen = t_data['gen_engineers'] * 1000 * market['gen_bottleneck_factor']
                    gen_actual_prod = min(cap_eq_gen, cap_hr_gen, t_data['gen_mat_inventory_qty'])
                    
                    if t_data['gen_mat_inventory_qty'] > 0:
                        used_mat_val = t_data['gen_mat_inventory_value'] * (gen_actual_prod / t_data['gen_mat_inventory_qty'])
                    else: used_mat_val = 0
                    
                    t_data['gen_mat_inventory_qty'] -= gen_actual_prod
                    t_data['gen_mat_inventory_value'] -= used_mat_val
                    
                    gen_mfg_cost = used_mat_val + gen_labor_cost + gen_dep_exp
                    t_data['gen_prod_inventory_qty'] = t_data.get('gen_prod_inventory_qty', 0) + gen_actual_prod
                    t_data['gen_prod_inventory_value'] = t_data.get('gen_prod_inventory_value', 0) + gen_mfg_cost
                    
                    adv_mat_cost = dec.get('adv_mat', 0) * market['adv_mat_price']
                    t_data['adv_mat_inventory_qty'] = t_data.get('adv_mat_inventory_qty', 0) + dec.get('adv_mat', 0)
                    t_data['adv_mat_inventory_value'] = t_data.get('adv_mat_inventory_value', 0) + adv_mat_cost
                    adv_labor_cost = (t_data['adv_engineers'] * market['adv_base_salary']) + (dec.get('adv_hire', 0) * market['adv_hiring_cost']) + (dec.get('adv_fire', 0) * market['adv_firing_cost'])
                    
                    cap_eq_adv = current_adv_equip_val * 1 * market['adv_bottleneck_factor']
                    cap_hr_adv = t_data['adv_engineers'] * 500 * market['adv_bottleneck_factor']
                    adv_actual_prod = min(cap_eq_adv, cap_hr_adv, t_data['adv_mat_inventory_qty'])
                    
                    if t_data['adv_mat_inventory_qty'] > 0:
                        used_adv_mat_val = t_data['adv_mat_inventory_value'] * (adv_actual_prod / t_data['adv_mat_inventory_qty'])
                    else: used_adv_mat_val = 0
                    
                    t_data['adv_mat_inventory_qty'] -= adv_actual_prod
                    t_data['adv_mat_inventory_value'] -= used_adv_mat_val
                    
                    adv_mfg_cost = used_adv_mat_val + adv_labor_cost + adv_dep_exp
                    t_data['adv_prod_inventory_qty'] = t_data.get('adv_prod_inventory_qty', 0) + adv_actual_prod
                    t_data['adv_prod_inventory_value'] = t_data.get('adv_prod_inventory_value', 0) + adv_mfg_cost
                    
                    t_data['temp_calc'] = {
                        'gen_actual_prod': gen_actual_prod, 'adv_actual_prod': adv_actual_prod,
                        'gen_mat_purchase': gen_mat_cost, 'adv_mat_purchase': adv_mat_cost,
                        'gen_labor': gen_labor_cost, 'adv_labor': adv_labor_cost,
                        'total_equip_val': total_equip_val, 'equity_ratio': equity_ratio,
                        'interest_rate': interest_rate, 'interest_exp': interest_exp
                    }

                def calc_market_scores(market_type, price_key, sga_key, dump_limit, high_limit):
                    eligible_teams = []
                    for t_name, t_data in all_teams_data.items():
                        price = t_data['current_decision'].get(price_key, 0)
                        if dump_limit <= price <= high_limit: eligible_teams.append(t_name)
                    
                    if not eligible_teams: return {t: 0 for t in all_teams_data.keys()}
                    
                    avg_price = sum(all_teams_data[t]['current_decision'].get(price_key, 0) for t in eligible_teams) / len(eligible_teams)
                    avg_sga = sum(all_teams_data[t]['current_decision'].get(sga_key, 0) for t in eligible_teams) / len(eligible_teams) + 1
                    
                    scores = {}
                    for t_name in all_teams_data.keys():
                        if t_name in eligible_teams:
                            dec = all_teams_data[t_name]['current_decision']
                            p_score = avg_price / dec.get(price_key, 1) if dec.get(price_key, 1) > 0 else 1
                            s_score = dec.get(sga_key, 0) / avg_sga
                            scores[t_name] = (p_score * 0.7) + (s_score * 0.3)
                        else:
                            scores[t_name] = 0
                    return scores

                gen_scores = calc_market_scores('generic', 'gen_price', 'gen_sga', market['gen_dumping_limit'], market['gen_high_price_limit'])
                adv_scores = calc_market_scores('advanced', 'adv_price', 'adv_sga', market['adv_dumping_limit'], market['adv_high_price_limit'])
                
                gen_total_score = sum(gen_scores.values()) or 1
                adv_total_score = sum(adv_scores.values()) or 1

                for t_name, t_data in all_teams_data.items():
                    dec = t_data['current_decision']
                    tc = t_data['temp_calc']
                    
                    gen_alloc = int(market['gen_total_demand'] * (gen_scores[t_name] / gen_total_score))
                    gen_sales_qty = min(gen_alloc, t_data['gen_prod_inventory_qty'])
                    gen_unit_cost = t_data['gen_prod_inventory_value'] / t_data['gen_prod_inventory_qty'] if t_data['gen_prod_inventory_qty'] > 0 else 0
                    gen_revenue = gen_sales_qty * dec.get('gen_price', 0)
                    gen_cogs = gen_sales_qty * gen_unit_cost
                    t_data['gen_prod_inventory_qty'] -= gen_sales_qty
                    t_data['gen_prod_inventory_value'] -= gen_cogs
                    
                    adv_alloc = int(market['adv_total_demand'] * (adv_scores[t_name] / adv_total_score))
                    adv_sales_qty = min(adv_alloc, t_data['adv_prod_inventory_qty'])
                    adv_unit_cost = t_data['adv_prod_inventory_value'] / t_data['adv_prod_inventory_qty'] if t_data['adv_prod_inventory_qty'] > 0 else 0
                    adv_revenue = adv_sales_qty * dec.get('adv_price', 0)
                    adv_cogs = adv_sales_qty * adv_unit_cost
                    t_data['adv_prod_inventory_qty'] -= adv_sales_qty
                    t_data['adv_prod_inventory_value'] -= adv_cogs
                    
                    gen_loss = (t_data['gen_mat_inventory_value'] + t_data['gen_prod_inventory_value']) * market['gen_inventory_cost_rate']
                    adv_loss = (t_data['adv_mat_inventory_value'] + t_data['adv_prod_inventory_value']) * market['adv_inventory_cost_rate']
                    valuation_loss = gen_loss + adv_loss
                    
                    t_data['gen_mat_inventory_value'] *= (1 - market['gen_inventory_cost_rate'])
                    t_data['gen_prod_inventory_value'] *= (1 - market['gen_inventory_cost_rate'])
                    t_data['adv_mat_inventory_value'] *= (1 - market['adv_inventory_cost_rate'])
                    t_data['adv_prod_inventory_value'] *= (1 - market['adv_inventory_cost_rate'])

                    total_revenue = gen_revenue + adv_revenue
                    total_cogs = gen_cogs + adv_cogs
                    gross_profit = total_revenue - total_cogs
                    total_sga = dec.get('gen_sga', 0) + dec.get('adv_sga', 0)
                    op_profit = gross_profit - total_sga
                    
                    pre_tax_income = op_profit - tc['interest_exp'] - valuation_loss
                    tax = pre_tax_income * market['tax_rate'] if pre_tax_income > 0 else 0
                    net_income = pre_tax_income - tax
                    
                    cash_out = (dec.get('gen_invest', 0) + dec.get('adv_invest', 0) + 
                                tc['gen_mat_purchase'] + tc['adv_mat_purchase'] + 
                                tc['gen_labor'] + tc['adv_labor'] + 
                                total_sga + tc['interest_exp'] + tax)
                    t_data['cash'] += (total_revenue - cash_out)
                    
                    if t_data['cash'] < 0:
                        shortfall = -t_data['cash']
                        t_data['emergency_debt'] = t_data.get('emergency_debt', 0) + shortfall
                        t_data['cash'] = 0 
                        
                    t_data['retained_earnings'] = t_data.get('retained_earnings', 0) + net_income
                    
                    final_assets = (t_data['cash'] + t_data['gen_mat_inventory_value'] + t_data['gen_prod_inventory_value'] +
                                    t_data['adv_mat_inventory_value'] + t_data['adv_prod_inventory_value'] + tc['total_equip_val'])
                    
                    if 'history' not in t_data: t_data['history'] = {}
                    t_data['history'][str(market['turn'])] = {
                        'revenue': total_revenue, 'cogs': total_cogs, 'gross_profit': gross_profit,
                        'sga': total_sga, 'op_profit': op_profit, 'interest_exp': tc['interest_exp'],
                        'valuation_loss': valuation_loss, 'pre_tax_income': pre_tax_income,
                        'tax': tax, 'net_income': net_income,
                        
                        'gen_price': dec.get('gen_price', 0), 'adv_price': dec.get('adv_price', 0),
                        'equity_ratio': tc['equity_ratio'], 'interest_rate': tc['interest_rate'],
                        'total_equip_value': tc['total_equip_val'], 'total_assets': final_assets,
                        'end_retained_earnings': t_data['retained_earnings']
                    }
                    
                    del t_data['temp_calc']
                    t_data['decision_submitted'] = False
                    
                    batch.set(db.collection('teams').document(t_name), t_data)

                batch.update(db.collection('market_state').document('current'), {'turn': market['turn'] + 1})
                batch.commit()
                
                st.success(f"✅ 第 {market['turn']} 期の決算処理が完了しました！")
                st.rerun()
        else:
            st.warning("全チームの意思決定が出揃うまで、ターン処理は実行できません。")
            
    elif admin_pass != "":
        st.error("パスワードが間違っています。")