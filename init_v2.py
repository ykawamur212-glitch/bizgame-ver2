import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Ver.2 データベース初期化ツール")

# Firebaseの初期化
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"認証エラー: firebase_key.json がこのフォルダに存在するか確認してください。詳細: {e}")
        st.stop()

db = firestore.client()

st.title("Ver.2 ゲームデータ 初期化ツール")
st.warning("⚠️ 実行すると、現在のデータベースの内容が Ver.2 用の新しい構造（5チーム、2製品ライン等）で完全に上書きされます。")

if st.button("Ver.2の初期データベースを構築する", type="primary"):
    try:
        # --- 市場環境データ (Ver.2用拡張版) ---
        db.collection('market_state').document('current').set({
            'turn': 1,
            'tax_rate': 0.40, # 法人税 40%
            'base_interest_rate': 0.05, # 基準金利 5%
            
            # 汎用品 (Generic) の市場パラメータ
            'gen_total_demand': 80000,
            'gen_mat_price': 5,
            'gen_base_salary': 3000,
            'gen_hiring_cost': 500,
            'gen_firing_cost': 1000,
            'gen_inventory_cost_rate': 0.1, # 在庫評価損率 10%
            'gen_dumping_limit': 15, # これ未満の価格は売上0
            'gen_high_price_limit': 100, # これを超える価格は売上0
            'gen_bottleneck_factor': 1.0, # 管理者が変動させる景気係数
            
            # 先端品 (Advanced) の市場パラメータ
            'adv_total_demand': 30000,
            'adv_mat_price': 20,
            'adv_base_salary': 8000,
            'adv_hiring_cost': 2000,
            'adv_firing_cost': 4000,
            'adv_inventory_cost_rate': 0.2, # 先端品は陳腐化が早い (20%)
            'adv_dumping_limit': 50,
            'adv_high_price_limit': 300,
            'adv_bottleneck_factor': 1.0, # 管理者が変動させる景気係数
        })
        
        # --- 5チーム分のデータ (Ver.2用拡張版) ---
        teams = ["Team A", "Team B", "Team C", "Team D", "Team E"]
        team_pins = {"Team A": "1111", "Team B": "2222", "Team C": "3333", "Team D": "4444", "Team E": "5555"}
        
        batch = db.batch()
        for t in teams:
            ref = db.collection('teams').document(t)
            batch.set(ref, {
                'pin': team_pins[t],
                
                # 財務情報
                'cash': 100000, # 初期資金を少し多めに設定
                'capital': 100000,
                'retained_earnings': 0,
                'debt': 0, # 借入金
                
                # 汎用品 (Generic) 部門
                'gen_equipment_list': [],
                'gen_engineers': 0,
                'gen_mat_inventory_qty': 0,
                'gen_mat_inventory_value': 0,
                'gen_prod_inventory_qty': 0,
                'gen_prod_inventory_value': 0,
                
                # 先端品 (Advanced) 部門
                'adv_equipment_list': [],
                'adv_engineers': 0,
                'adv_mat_inventory_qty': 0,
                'adv_mat_inventory_value': 0,
                'adv_prod_inventory_qty': 0,
                'adv_prod_inventory_value': 0,
                
                'history': {},
                'decision_submitted': False,
                'current_decision': {}
            })
        batch.commit()
        st.success("✅ Ver.2 データベースの構築に成功しました！")
    except Exception as e:
        st.error(f"❌ エラーが発生しました: {e}")

st.markdown("---")
market_doc = db.collection('market_state').document('current').get()
if market_doc.exists:
    st.write("現在の市場環境 (Ver.2):", market_doc.to_dict())

