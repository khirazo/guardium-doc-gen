# guardium-doc-gen
Python実行環境から Guardium Data Protection に接続し、REST API経由でポリシールールの情報を収集して、ファイルまたは STDOUT にCSV形式で出力するスクリプトです。

動作確認は、以下の開発環境で行っています。

- Python Client: Windows 11 上の Python 3.10.11
- GDP: 12.1.0_r118038_v12_1_1-el94-20240908_2158 (スタンドアロン)

## 事前準備

### OAuth クライアントの登録

GDP で REST API を使用するには、OAuthクライアントを登録する必要があります。(初回のみ)

CLI でコレクターにログインし、以下の grdapi コマンドを発行してアプリケーションを登録します。(この例では client_id は client1)

```shell
grdapi register_oauth_client client_id=client1 grant_types="password"
```

以下と類似した戻り値が返ってきますので、この中から "client_id" と "client_secret" の値を、後述する構成ファイル(JSON) に設定してください。

```json
{"client_id":"client1","client_secret":"b1f242a2-1e86-46d6-bf42-6298556c2eea","grant_types":"password"}
```

詳しくは 製品マニュアル [Guardium REST API の使用 - IBM Documentation](https://www.ibm.com/docs/ja/gdp/12.x?topic=commands-using-guardium-rest-apis) を参照してください。

### 構成ファイルの設定

grd_config.json ファイル (JSON) に、以下のパラメーターを設定します。

| パラメーター名 | 値の例                               | 説明                                                |
| -------------- | ------------------------------------ | --------------------------------------------------- |
| host_name      | 192.168.254.70                       | GDP のホスト名またはIPアドレス                      |
| port           | 8443                                 | GDP のポート番号                                    |
| client_id      | client1                              | register_oauth_client で事前定義した クライアントID |
| client_secret  | b1f242a2-1e86-46d6-bf42-6298556c2eea | register_oauth_client で事前取得した シークレット   |

構成ファイルの設定例は、以下のとおりです。

```json
{
  "host_name": "192.168.254.70",
  "port": 8443,
  "client_id": "client1",
  "client_secret": "b1f242a2-1e86-46d6-bf42-6298556c2eea"
}
```

構成ファイルは、Pythonスクリプト本体 (.py) と同じフォルダーに置いてください。

## 使用方法

コマンドの使用方法は、以下の通りです。

```shell
usage: doc_grd_policy_rules.py [-h] -u USERNAME -w PASSWORD [-o OUTPUT_FILE]

Output Guardium policy rules in CSV format

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Guardium admin user name
  -w PASSWORD, --password PASSWORD
                        Guardium admin user password
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        Output file name. STDOUT if omitted
```

### パラメーターの説明

| パラメーター名          | 必須 | 値の例        | 説明                                          |
| ----------------------- | ---- | ------------- | --------------------------------------------- |
| -h または --help        | No   |               | 上記のヘルプメッセージを表示して終了          |
| -u または --username    | Yes  | -u admin      | GDP の 管理ユーザー名を指定                   |
| -w または --password    | Yes  | -w P@ssw0rd   | GDP の 管理ユーザーパスワードを指定           |
| -o または --output_file | No   | -o output.csv | 出力ファイル名を指定 (省略した場合は標準出力) |

内部で繰り返しREST APIを発行しているため、実行完了までしばらく時間がかかります。API操作は読み取りのみで、GDPへの書き込み操作はありません。

Pythonの前提ライブラリーがインストールされていない場合はエラーとなります。エラー内容を確認し、pipコマンドでインストールしてください。
