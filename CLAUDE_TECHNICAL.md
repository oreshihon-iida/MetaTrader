# MetaTrader Technical Documentation - TECHNICAL

[← メインに戻る](./CLAUDE_MAIN.md)

---

## 🛠️ MT5開発必須コマンド集

### MQL5コンパイル
```bash
"C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\[ファイル名].mq5"

# 例: v21.7k戦略
"C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\MultiTimeframeConfluence_v21_7k_Phase1.mq5"
```

### ex5ファイル実行（MT5認識用）
```bash
start "" "C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\[ファイル名].ex5"
```

### MT5強制終了
```bash
TASKKILL /F /IM terminal64.exe
# 注意: 既に終了している場合はエラーメッセージが出るが正常動作
```

### MT5バックテスト実行
```bash
"C:\Program Files\MetaTrader 5\terminal64.exe" /auto /config:"C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\[設定ファイル名].ini"
```

### CSV結果ファイル検索
```bash
find "C:\Users\iida\AppData\Roaming\MetaQuotes\Tester" -name "*[戦略名]*" -type f 2>nul
```

---

## 📝 tester.ini正しい設定形式

```ini
[Tester]  # [General]ではない！必ず[Tester]
Expert=MultiTimeframeConfluence_v21_7k_Phase1  # Experts\プレフィックスなし！
Symbol=USDJPY
Period=H4
Login=  # 空欄でOK
Model=1
ExecutionMode=0
Optimization=0
OptimizationCriterion=0
FromDate=2024.01.01
FromTime=00:00
ToDate=2024.12.31
ToTime=00:00
ForwardMode=0
ForwardDate=
Report=tester\v21_7k_Phase1_Result
ReplaceReport=1
ShutdownTerminal=1  # CSV出力に必須！
Deposit=3000000.00
Currency=JPY
Leverage=1:25
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
```

---

## 📂 重要なディレクトリパス

- **MetaTrader 5インストール**: `C:\Program Files\MetaTrader 5\`
- **ユーザーデータルート**: `C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\`
- **Expert Advisors**: `MQL5\Experts\`
- **テスト設定ファイル**: ルート直下（上記ユーザーデータルート）
- **CSV出力先**: `C:\Users\iida\AppData\Roaming\MetaQuotes\Tester\D0E8209F77C8CF37AD8BF550E51FF075\Agent-127.0.0.1-3000\MQL5\Files\`
- **HTMLレポート**: `C:\Users\iida\Downloads\ReportTester-*.html`

---

## 🔧 完全ワークフロー

```bash
# Step 1: 戦略コンパイル
"C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\[戦略名].mq5"

# Step 2: コンパイル成功確認
dir "C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\[戦略名].ex5"

# Step 3: MT5プロセス終了
TASKKILL /F /IM terminal64.exe

# Step 4: バックテスト実行
"C:\Program Files\MetaTrader 5\terminal64.exe" /auto /config:"C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\tester_[戦略名].ini"

# Step 5: CSV結果確認
find "C:\Users\iida\AppData\Roaming\MetaQuotes\Tester" -name "*[戦略名]*" -type f 2>nul

# Step 6: 結果分析（Pythonスクリプト実行）
cd "C:\Users\iida\Documents\MetaTrader" && python analyze_[戦略名]_results.py
```

---

## ⚠️ よくあるエラーと解決法

### コンパイルエラー
- **テスト実行されない** → `[Tester]`セクション名を確認（`[General]`は誤り）
- **Expert not found** → Expert=から`Experts\`プレフィックスを削除
- **CSV生成されない** → `ShutdownTerminal=1`に設定
- **コンパイル失敗** → `/log`パラメータを削除
- **ダブルパスエラー** → `Experts\Experts\`となっていないか確認

### enum型変換エラーの修正
```mql5
// ❌ エラーとなるコード
WriteTradeToCSV("CLOSE", position.PositionType(), price, lot, 0, 0, 0, "pattern");

// ✅ 修正後のコード
ENUM_ORDER_TYPE orderType = (position.PositionType() == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
WriteTradeToCSV("CLOSE", orderType, price, lot, 0, 0, 0, "pattern");
```

### 詳細ログ出力
```bash
# コンパイルエラーの詳細確認
"C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"[ファイルパス]" /log:"C:\Users\iida\Documents\MetaTrader\compile_debug.log"

# ログ確認
type "C:\Users\iida\Documents\MetaTrader\compile_debug.log"
```

---

## 📊 HTMLレポート解析パターン

```python
# HTMLレポート解析用正規表現パターン
verification_patterns = {
    'total_trades': r'取引数:.*?<b>(\d+)</b>',
    'short_trades': r'ショート.*?<b>(\d+).*?\(([\d.]+)%\)</b>',
    'long_trades': r'ロング.*?<b>(\d+).*?\(([\d.]+)%\)</b>',
    'net_profit': r'総損益:.*?<b>([-\s\d]+)</b>',
    'gross_profit': r'総利益:.*?<b>([\s\d]+)</b>',
    'gross_loss': r'総損失:.*?<b>([-\s\d]+)</b>',
    'profit_factor': r'プロフィットファクター:.*?<b>([\d.]+)</b>',
    'win_trades': r'勝ちトレード.*?<b>(\d+).*?\(([\d.]+)%\)</b>',
    'loss_trades': r'負けトレード.*?<b>(\d+).*?\(([\d.]+)%\)</b>',
    'expected_payoff': r'期待利得:.*?<b>([-\d.]+)</b>'
}
```

---

## 🔨 自動テストシステム

### 戦略専用configファイル
```
tester_v21_7k_phase1.ini             - v21.7k Phase 1用
tester_v21_7l_winrate.ini            - v21.7l Win Rate用
tester_eurjpy_v1_0.ini               - EUR/JPY v1.0用
tester_SmartAmateur_H4_CSV.ini       - 4時間足版
tester_SmartAmateur_H1_CSV.ini       - 1時間足版
```

### バッチファイル
- `mt5_smart_test.bat v2.0` - 戦略専用config対応
- `test_smart_h4.bat` - 4時間足版専用
- `test_smart_h1.bat` - 1時間足版専用
- `auto_backtest_final.bat` - 複数戦略連続テスト

---

## 💡 重要な注意事項

1. **絶対パス必須**: 全てのパスは絶対パスで指定し、ダブルクォートで囲む
2. **[Tester]セクション**: INIファイルは必ず`[Tester]`セクションを使用
3. **ex5拡張子なし**: Expert名に`.ex5`拡張子は含めない
4. **CSV出力**: `ShutdownTerminal=1`設定が必須
5. **エラー対応**: シンプル化による逃避ではなく、根本原因を特定し完全解決する

---

[← メインに戻る](./CLAUDE_MAIN.md) | [戦略一覧 →](./CLAUDE_STRATEGIES.md)
