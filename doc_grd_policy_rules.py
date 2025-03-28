"""
GDPのポリシールールをCSV出力するスクリプト

Created: 2025/03/26
"""

import argparse
import csv, json, sys, os
import requests, urllib3
import sqlite3
from pprint import pprint, pformat

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PARAM_FILE_NAME = "grd_config.json"

def load_parameters(filepath=None):
    # JSONファイルからパラメータを読み込む
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), PARAM_FILE_NAME)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

def bool_to_str(value):
    # bool値を 文字列に変換する
    return "true" if value else "false"

def create_and_populate_policy_table(conn, data):
    # ポリシーのリストを SQLiteテーブルに書き込む
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE policies (
            id TEXT,
            policy_description TEXT,
            policy_category TEXT,
            policy_baseline TEXT,
            log_flat TEXT,
            rules_on_flat TEXT,
            selective_audit_trail TEXT,
            audit_pattern TEXT,
            policy_level TEXT
        )
    ''')
    for item in data:
        cursor.execute('''
            INSERT INTO policies (id, policy_description, policy_category, policy_baseline, log_flat, rules_on_flat, selective_audit_trail, audit_pattern, policy_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.get('id'),
            item.get('policy_description'),
            item.get('policy_category'),
            item.get('policy_baseline'),
            item.get('log_flat'),
            item.get('rules_on_flat'),
            item.get('selective_audit_trail'),
            item.get('audit_pattern'),
            item.get('policy_level')
        ))
    conn.commit()

def create_rule_table(conn):
    # ポリシールールのリストを格納する SQLiteテーブルを作成する
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE policy_rules (
            policyName TEXT,
            policyType TEXT,
            category TEXT,
            installed TEXT,
            logFlat TEXT,
            rulesOnFlat TEXT,
            auditPattern TEXT,
            ruleName TEXT,
            ruleType TEXT,
            ruleLevel TEXT,
            severity TEXT,
            continueToNextRule TEXT,
            parameters TEXT,
            actions TEXT,
            policyLevel TEXT
        )
    ''')
    conn.commit()

def populate_rule_table(conn, data):
    # ポリシールールのリストを SQLiteテーブルに書き込む
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO policy_rules (policyName, policyType, category, installed, logFlat, rulesOnFlat, auditPattern, ruleName, ruleType, ruleLevel, severity, continueToNextRule, parameters, actions, policyLevel)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('policyName'),
        data.get('policyType'),
        data.get('category'),
        bool_to_str(data.get('installed')),
        bool_to_str(data.get('logFlat')),
        bool_to_str(data.get('rulesOnFlat')),
        data.get('auditPattern'),
        data.get('ruleName'),
        data.get('ruleType'),
        data.get('ruleLevel'),
        data.get('severity'),
        bool_to_str(data.get('continueToNextRule')),
        pformat(data.get('parameters'), sort_dicts=False),
        pformat(data.get('actions'), sort_dicts=False),
        data.get('policyLevel')
    ))
    conn.commit()

def get_joined_data_with_headers(conn):
    # 2つの SQLiteテーブルの内容を JOINして返す
    cursor = conn.cursor()
    cursor.execute('''
        SELECT *
        FROM policies
        JOIN policy_rules ON policies.policy_description = policy_rules.policyName
    ''')
    rows = cursor.fetchall()
    headers = [description[0] for description in cursor.description]
    # print(headers)
    # for row in rows:
    #     print(row)
    return headers, rows

def exit_program(code=0, conn=None):
    # 終了コードの集約
    if conn:
        conn.close()
    sys.exit(code)

def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="Output Guardium policy rules in CSV format")
    parser.add_argument("-f", "--filepath", help=f"Config file(json) path. Use {PARAM_FILE_NAME} if omitted")
    parser.add_argument("-u", "--username", required=True, help="Guardium admin user name")
    parser.add_argument("-w", "--password", required=True, help="Guardium admin user password")
    parser.add_argument("-o", "--output_file", help="Output file name. STDOUT if omitted")
    args = parser.parse_args()

    # パラメーターをJSONファイルから読み込む
    params = load_parameters(args.filepath)

    if params:
        # print(params)
        host_name = params.get("host_name") # Guardium のホスト名またはIPアドレス
        port = params.get("port")           # Guardium のポート番号
        client_id = params.get("client_id") # Guardium の CLI で事前登録したID
        client_secret = params.get("client_secret") # Guardium の CLI で事前登録したシークレット
    else:
        print(f"{PARAM_FILE_NAME} からパラメーターの読み込みに失敗しました。")
        exit_program(1)

    server_url = f"https://{host_name}:{port}"
    
    # Guardium APIへのアクセス
    ## アクセストークンの取得
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "password",
        "username": args.username,
        "password": args.password
    }
    # print(data)

    response_json = {}
    try:
        response = requests.post(f"{server_url}/oauth/token", data=data, verify=False)
        response.raise_for_status()  # 2xx以外なら中断
        response_json = response.json()
        # print(response_json)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        exit_program(1)

    access_token = response_json.get("access_token")
    # print(access_token)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # メモリー上の SQLiteデータベースに接続
    conn = sqlite3.connect(':memory:')

    ## ポリシーデータの取得
    response_json = {}
    try:
        response = requests.get(f"{server_url}/restAPI/policy", headers=headers, verify=False)
        response.raise_for_status()  # 2xx以外なら中断
        response_json = response.json()
        # print(response_json)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        exit_program(1, conn)
   
    # Policyテーブルの作成とデータ投入
    create_and_populate_policy_table(conn, response_json)

    # Policy Descriptionのリストを取得 (ルールの検索に使用する)
    policy_descriptions = [item.get('policy_description') for item in response_json]

    # Policy Rule テーブル作成
    create_rule_table(conn)

    ## ポリシールールのデータを取得 (1つのポリシーに複数のルールが紐づいている)
    for policy in policy_descriptions:
        params = { "policyDesc": policy }
        response_json = {}
        try:
            response = requests.get(f"{server_url}/restAPI/ruleInfoFromPolicy", headers=headers, params=params, verify=False)
            response.raise_for_status()  # 2xx以外なら中断
            response_json = response.json()
            # pprint(response_json, sort_dicts=False)
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            exit_program(1, conn)
        
        policy = {}
        policy = response_json[0]   # レスポンスにポリシーは1つしか含まれていない
        # print(policy)

        # ルールのリストをループ (ルール以外のポリシー属性は同じ値が続く)
        rules = policy.get('rules')
        for item in rules:
            data = {
                'policyName': policy.get('policyName'),
                'policyType': policy.get('policyType'),
                'category': policy.get('category'),
                'installed': policy.get('installed'),
                'logFlat': policy.get('logFlat'),
                'rulesOnFlat': policy.get('rulesOnFlat'),
                'auditPattern': policy.get('auditPattern'),
                'ruleName': item.get('ruleName'),
                'ruleType': item.get('ruleType'),
                'ruleLevel': item.get('ruleLevel'),
                'severity': item.get('severity'),
                'continueToNextRule': item.get('continueToNextRule'),
                'parameters': item.get('parameters'),
                'actions': item.get('actions'),
                'policyLevel': policy.get('policyLevel')
            }

            # Policy Ruleテーブルへのデータ挿入
            populate_rule_table(conn, data)

    # SQLiteのテーブル情報をリストで取得
    headers, data = get_joined_data_with_headers(conn)

    # CSVファイルへの書き込み (Excel を想定して UTF-8 BOM 形式を使用)
    if args.output_file:
        try:
            with open(args.output_file, "w", newline="", encoding="utf-8-sig") as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                writer.writerow(headers)    # ヘッダーを書き込む
                writer.writerows(data)      # 行を書き込む
            print(f"CSVファイルを {args.output_file} に出力しました。")
        except Exception as e:
            print(f"エラーが発生しました: {e}")
    else:
        writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
        writer.writerows(data)

    exit_program(0, conn)

if __name__ == "__main__":
    main()