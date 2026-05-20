import streamlit as st
import json
import csv
import random
import urllib.parse
import re
import requests           # ← これを追加
from PIL import Image     # ← これを追加
from io import BytesIO    # ← これを追加
from google import genai

# ... (以降は元のコード) ...

# ==========================================
# 0. 初期設定とセッション管理
# ==========================================
st.set_page_config(page_title="プロンプトエンジニアリング学習SaaS", page_icon="🧠", layout="wide")
MODEL_NAME = "gemini-2.5-flash"
CSV_FILENAME = "prompt_dataset.csv"

# Webアプリの「一時記憶」をセットアップ（画面更新で消えないようにする）
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "text_scenario" not in st.session_state:
    st.session_state.text_scenario = ""
if "image_situation" not in st.session_state:
    st.session_state.image_situation = ""
if "image_url" not in st.session_state:
    st.session_state.image_url = ""

# ==========================================
# 1. 汎用関数
# ==========================================
def robust_parse_json(text):
    """AIの出力から強制的にJSONを抽出するフィルター"""
    text = re.sub(r'^```.*?$', '', text, flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError("JSONの形式が見つかりませんでした。")
    while isinstance(data, list):
        if len(data) > 0:
            data = data[0]
        else:
            raise ValueError("空のリストが返されました。")
    return data

@st.cache_data # Streamlit特有の機能：CSVを一度だけ読み込んで高速化する
def load_csv_data(filename):
    encodings = ['utf-8', 'utf-8-sig', 'shift_jis', 'cp932']
    for enc in encodings:
        data_list = []
        try:
            with open(filename, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    weak = row.get("Original weak/vague prompt") or row.get("weak_prompt") or ""
                    effective = row.get("Improved effective prompt") or row.get("effective_prompt") or ""
                    if weak and effective:
                        data_list.append({"bad_example": weak.strip(), "good_example": effective.strip()})
            return data_list
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return []

csv_dataset = load_csv_data(CSV_FILENAME)

# ==========================================
# 2. サイドバー（APIキー設定）
# ==========================================
with st.sidebar:
    st.header("⚙️ 設定")
    api_key = st.text_input("Gemini API Key を入力", type="password", help="セキュリティのため、ここにAPIキーを入力してください。")
    st.markdown("---")
    st.markdown("データセット連携状態:")
    if csv_dataset:
        st.success(f"✅ Kaggleデータ連携中 ({len(csv_dataset)}件)")
    else:
        st.warning("⚠️ CSV未連携 (標準モデルで動作)")

if not api_key:
    st.warning("👈 左側のサイドバーにGemini API Keyを入力してアプリを開始してください。")
    st.stop() # キーがない場合はここで処理を止める

client = genai.Client(api_key=api_key)

# ==========================================
# 3. メイン画面とタブ構築
# ==========================================
st.title("🧠 AIプロンプト・マスタリー")
st.markdown("AIの性能を100%引き出すための、視覚的・帰納的トレーニングプラットフォーム")

tab1, tab2, tab3, tab4 = st.tabs(["📖 教科書", "💡 クイズ(4択)", "📝 文字モード", "🖼️ 画像モード"])

# ------------------------------------------
# 【タブ1】📖 教科書
# ------------------------------------------
with tab1:
    st.header("プロンプトエンジニアリングの基本原則")
    st.markdown("""
    AIから期待通りの結果を引き出すためには、AIを「優秀なアシスタント」として扱い、明確な指示を与えることが重要です。以下の「3つの原則」を意識してプロンプトを作成しましょう。
    
    ### 💡 原則1：役割（ペルソナ）を明確にする
    AIに「誰」として振る舞ってほしいかを指定すると、回答の精度と専門性が飛躍的に向上します。
    * ❌ 悪い例：「〜について教えて」
    * ⭕ 良い例：「あなたは優秀なデータサイエンティストです。〜について教えてください」
    
    ### 💡 原則2：背景と目的（コンテキスト）を共有する
    なぜその情報が必要なのか、最終的にどうしたいのかを伝えないと、AIは一般的な回答しかできません。
    * ❌ 悪い例：「議事録をまとめて」
    * ⭕ 良い例：「明日の経営会議で報告するため、以下の商談メモから『決定事項』と『懸念点』を抽出してまとめてください」
    
    ### 💡 原則3：出力形式と制約（フォーマット）を定義する
    文字数、形式（箇条書き、表、Markdownなど）、使ってはいけない言葉などを明確に指定します。
    
    ---
    ### 【実践例：計算エラーのトラブルシューティング】
    AIに高度な専門作業を依頼する際の効果的なプロンプト例です。
    
    **❌ 悪いプロンプト**
    > 「計算がエラーで止まりました。どうすればいいですか？」
    
    **⭕ 良いプロンプト**
    > 「あなたは優秀な計算化学の研究パートナーです。
    > 現在、Gaussianを使用してTD-DFT計算を行っていますが、SCF収束エラーが発生してストップしてしまいました。
    > インプットファイルでは汎関数にB3LYP、基底関数にdef2-SVPを指定しています。
    > 以下のエラーログの抜粋を確認し、考えられる原因と、修正案を箇条書きで提案してください。」
    """)

# ------------------------------------------
# 【タブ2】💡 クイズ(4択)
# ------------------------------------------
with tab2:
    st.header("足りない情報を見抜くトレーニング")
    
    if st.button("新しいクイズを出題する", type="primary", key="btn_quiz"):
        instruction = """
        プロンプトエンジニアリングのクイズを出題します。日常トラブルの「悪いプロンプト」を提示し、【最も追加すべき情報】を4択で出題してください。
        必ず以下のJSON形式のみで出力してください。
        {
          "scenario": "メルカリでクレームを受けた",
          "bad_prompt": "返信を書いて",
          "choices": ["自分の感情", "クレームの具体的内容", "会社の住所", "相手の名前"],
          "correct_index": 1,
          "explanation": "状況指定が最重要だからです。"
        }
        """
        with st.spinner("AIがクイズを作成中..."):
            try:
                response = client.models.generate_content(model=MODEL_NAME, contents=instruction)
                st.session_state.quiz_data = robust_parse_json(response.text)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    if st.session_state.quiz_data:
        q_data = st.session_state.quiz_data
        st.info(f"**【トラブルの状況】**\n{q_data['scenario']}\n\n**【悪いプロンプト例】**\n{q_data['bad_prompt']}")
        
        # Streamlitのラジオボタンを使用して4択を実装
        selected = st.radio("▼ 足りないと思う情報を選んでください ▼", q_data['choices'], index=None)
        
        if st.button("回答する") and selected:
            correct_choice = q_data['choices'][q_data['correct_index']]
            if selected == correct_choice:
                st.success("🎉 大正解！")
            else:
                st.error(f"❌ ざんねん、不正解...\n\n正解は「**{correct_choice}**」でした。")
            st.markdown(f"**【解説】**\n{q_data['explanation']}")

# ------------------------------------------
# 【タブ3】📝 文字モード
# ------------------------------------------
with tab3:
    st.header("状況提示型プロンプト作成")
    
    if st.button("文字のお題を生成", type="primary", key="btn_text"):
        instruction = "あなたは試験官です。日常トラブルをランダムに1つ作成してください。\n【お題のタイトル】\n【具体的な状況】\n【AIに指示すべき制約条件】"
        with st.spinner("お題を生成中..."):
            try:
                res = client.models.generate_content(model=MODEL_NAME, contents=instruction)
                st.session_state.text_scenario = res.text
            except Exception as e:
                st.error(f"エラー: {e}")

    if st.session_state.text_scenario:
        st.info(st.session_state.text_scenario)
        
        user_prompt_text = st.text_area("▼ あなたのプロンプトを入力 ▼", height=150)
        
        if st.button("このプロンプトで採点する", key="eval_text"):
            if not user_prompt_text:
                st.warning("プロンプトを入力してください。")
            else:
                ref_json = json.dumps(random.sample(csv_dataset, min(3, len(csv_dataset))), ensure_ascii=False) if csv_dataset else "基準データなし"
                eval_inst = f"""提示された【お題】に対するユーザーのプロンプトを100点満点で採点してください。
                以下の【基準データセット（JSON）】から法則を帰納的に推論し、評価に反映させてください。
                【基準データセット】\n{ref_json}\n\n【お題】\n{st.session_state.text_scenario}\n\n【ユーザーのプロンプト】\n{user_prompt_text}
                【出力】\n【合計スコア】〇〇点\n【データから推論された評価の根拠】\n【改善のポイント】"""
                
                with st.spinner("帰納的データから採点中..."):
                    try:
                        res = client.models.generate_content(model=MODEL_NAME, contents=eval_inst)
                        st.success("採点完了！")
                        st.write(res.text)
                    except Exception as e:
                        st.error(f"エラー: {e}")

# ------------------------------------------
# 【タブ4】🖼️ 画像モード
# ------------------------------------------
with tab4:
    st.header("言語化能力テスト（画像分析）")
    
    if st.button("画像のお題を生成", type="primary", key="btn_img"):
        instruction = """日常のトラブルの「写真」を1枚想像し、必ず以下の形式で1つだけJSON出力してください。
        【重要】"situation"には、写真に写っている「視覚的に確認できる事実（物理的な状態）」のみを書いてください。見えない背景事情は含めないで。
        {
            "situation": "画像から見て取れる物理的な状況の詳細（日本語）",
            "image_prompt": "画像生成用プロンプト（英語。Photorealistic）"
        }"""
        
        with st.spinner("AIが画像のお題を生成中... (約10秒)"):
            try:
                res = client.models.generate_content(model=MODEL_NAME, contents=instruction)
                data = robust_parse_json(res.text)
                
                st.session_state.image_situation = data.get("situation", "不明な状況")
                image_prompt = data.get("image_prompt", "error")
                
                encoded_prompt = urllib.parse.quote(image_prompt)
                st.session_state.image_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){encoded_prompt}?width=800&height=450&nologo=true"
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    if st.session_state.image_url:
        # StreamlitならURLを渡すだけで綺麗に画像を表示してくれます
        st.image(st.session_state.image_url, use_container_width=True)
        
        user_img_prompt = st.text_area("▼ 状況の説明 ＋ 解決の指示を入力 ▼", height=150)
        
        if st.button("この状況説明で採点する", key="eval_img"):
            if not user_img_prompt:
                st.warning("プロンプトを入力してください。")
            else:
                eval_inst = f"""あなたは客観的な評価者です。実際の状況とユーザーの入力を比較し採点してください。
                
                【実際の状況（画像に写っている事実）】\n{st.session_state.image_situation}\n\n【ユーザーの入力】\n{user_img_prompt}
                
                【評価基準】
                1. 状況説明能力（50点）: 画像から「視覚的に読み取れる物理的な状況」を正確に言語化できているか。（※推測不可能な背景事情を要求して減点しないこと）
                2. 目的達成度（50点）: ユーザーが設定した役割や目的に沿って、トラブルを解決するための適切な指示ができているか。
                
                【出力】\n【合計スコア】〇〇点\n【評価の根拠】\n【理想のプロンプト例】"""
                
                with st.spinner("状況説明能力を採点中..."):
                    try:
                        res = client.models.generate_content(model=MODEL_NAME, contents=eval_inst)
                        st.success("採点完了！")
                        st.write(res.text)
                    except Exception as e:
                        st.error(f"エラー: {e}")