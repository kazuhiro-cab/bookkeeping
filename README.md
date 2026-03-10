# Bookkeeping

会計処理練習ツールの実装ベースです。以下を含みます。

- 学習者管理、学習モード切替、セッション生成
- 問題登録（手動/CSV）、問題状態管理、改訂履歴保持
- 回答保存（上書きせず履歴保持）と採点結果分離保存
- 許容解・採点ルールに基づく採点（税金仕訳の前提一致判定を含む）
- 解説表示、帳簿/財務諸表/原価計算影響データ参照
- 学習履歴、弱点分析、結果エクスポート
- 著作権区分に基づく出題制御
- GUI（Tkinter）による学習フローの基本操作

## Windows (venv 前提)

本リポジトリは `venv` を利用して実行します。

1. 依存関係セットアップ

```bat
setup.bat
```

2. GUI起動

```bat
run.bat
```

3. テスト実行

```bat
run_tests.bat
```

## 手動実行

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m bookkeeping_app
python -m unittest discover -s tests
```
