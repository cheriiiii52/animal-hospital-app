from flask import Flask, request, redirect, render_template_string
import json, os
from datetime import datetime

app = Flask(__name__)
FILE = 'data.json'

# 데이터 불러오기
if os.path.exists(FILE):
    data = json.load(open(FILE, encoding='utf-8'))
else:
    data = []

def save():
    json.dump(data, open(FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def money(x):
    return f"{int(x):,}"

@app.route('/')
def index():
    selected_date = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')

    selected_month = selected_date[:7]
    selected_year = selected_date[:4]

    def is_real_sale(i):
        return i.get('method') != '예치금' or i.get('type') == '충전'

    daily_data = [i for i in data if i.get('date') == selected_date]
    monthly_data = [i for i in data if i.get('date','').startswith(selected_month)]
    yearly_data = [i for i in data if i.get('date','').startswith(selected_year)]

    daily = sum(int(i.get('amount',0)) for i in daily_data if is_real_sale(i))
    monthly = sum(int(i.get('amount',0)) for i in monthly_data if is_real_sale(i))
    yearly = sum(int(i.get('amount',0)) for i in yearly_data if is_real_sale(i))

    deposit_used = sum(int(i.get('amount',0)) for i in monthly_data if i.get('method') == '예치금')
    deposit_charge = sum(int(i.get('amount',0)) for i in monthly_data if i.get('type') == '충전')

    percent = (deposit_used / monthly * 100) if monthly else 0

    # 예치금 잔액
    balance = {}
    for i in data:
        key = f"{i.get('id','')} {i.get('name','')}"
        balance.setdefault(key, 0)

        if i.get('type') == '충전':
            balance[key] += int(i.get('amount',0))
        elif i.get('method') == '예치금':
            balance[key] -= int(i.get('amount',0))

    # 날짜별 묶기
    grouped = {}
    for i in sorted(monthly_data, key=lambda x: x.get('date',''), reverse=True):
        grouped.setdefault(i.get('date',''), []).append(i)

    html = """
    <html>
    <head>
    <style>
    body {
        font-family: -apple-system, BlinkMacSystemFont;
        background: #f8fafc;
        padding: 40px;
    }

    .box {
        background: white;
        padding: 25px;
        border-radius: 16px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    h3 {
        margin-bottom: 15px;
    }

    input, select {
        font-size: 16px;
        padding: 12px;
        width: 100%;
        margin-top: 10px;
        border: 1px solid #ddd;
        border-radius: 10px;
    }

    button {
        margin-top: 15px;
        padding: 14px;
        width: 100%;
        background: linear-gradient(135deg, #4CAF50, #66bb6a);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: bold;
        cursor: pointer;
    }

    button:hover {
        opacity: 0.9;
    }

    .grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-top: 15px;
    }

    .grid div {
        background: #f1f5f9;
        padding: 12px;
        border-radius: 10px;
    }

    .date {
        margin-top: 15px;
        font-weight: bold;
        font-size: 18px;
    }

    li {
        padding: 10px;
        border-bottom: 1px solid #eee;
    }

    li:hover {
        background: #f9fafb;
    }
    </style>
    </head>

    <body>

    <!-- 매출 입력 -->
    <div class="box">
        <h3>매출 입력</h3>
        <form action="/add" method="post">
            <input type="date" name="date" required>
            <input name="id" placeholder="동물번호" required>
            <input name="name" placeholder="이름" required>
            <input name="amount" placeholder="금액" required>

            <select name="method">
                <option value="카드">카드</option>
                <option value="현금">현금</option>
                <option value="계좌이체">계좌이체</option>
                <option value="예치금">예치금</option>
            </select>

            <select name="type">
                <option value="일반">일반</option>
                <option value="충전">예치금 충전</option>
            </select>

            <button>추가</button>
        </form>
    </div>

    <!-- 예치금 -->
    <div class="box">
        <h3>예치금 잔액</h3>
        <input id="search" placeholder="동물번호 / 이름 검색">
        <ul id="result"></ul>
    </div>

    <!-- 매출 통계 -->
    <div class="box">
        <h3>매출 통계</h3>

        <form method="get">
            <input type="date" name="date" value="{{selected_date}}">
            <button>조회</button>
        </form>

        <div class="grid">
            <div>일 매출: {{daily}}원</div>
            <div>월 매출: {{monthly}}원</div>
            <div>연 매출: {{yearly}}원</div>
            <div>예치금 결제: {{deposit_charge}}원</div>
            <div>예치금 사용: {{deposit_used}}원</div>
            <div>예치금 사용 비율: {{percent}}%</div>
        </div>
    </div>

    <!-- 매출 목록 -->
    <div class="box">
        <h3>매출 목록</h3>
        {% for d, items in grouped.items() %}
            <div class="date">📅 {{d}}</div>
            <ul>
            {% for item in items %}
                <li oncontextmenu="del('{{item.get('date')}}','{{item.get('name')}}','{{item.get('amount')}}'); return false;">
                {{item.get('id')}} {{item.get('name')}} |
                {{ "{:,}".format(item.get('amount')|int) }}원 |
                {{item.get('method')}}
                </li>
            {% endfor %}
            </ul>
        {% endfor %}
    </div>

    <script>
    function del(date, name, amount){
        if(confirm("삭제할까요?")){
            fetch('/delete', {
                method:'POST',
                headers: {'Content-Type':'application/x-www-form-urlencoded'},
                body: `date=${date}&name=${name}&amount=${amount}`
            }).then(()=>location.reload())
        }
    }

    const balance = {{balance|tojson}};
    const result = document.getElementById('result');

    document.getElementById('search').addEventListener('input', e=>{
        const q = e.target.value;
        result.innerHTML = '';
        if(!q) return;

        Object.keys(balance).forEach(k=>{
            if(k.includes(q)){
                const li = document.createElement('li');
                li.textContent = k + " : " + balance[k].toLocaleString() + "원";
                result.appendChild(li);
            }
        });
    });
    </script>

    </body>
    </html>
    """

    return render_template_string(
        html,
        grouped=grouped,
        daily=money(daily),
        monthly=money(monthly),
        yearly=money(yearly),
        deposit_used=money(deposit_used),
        deposit_charge=money(deposit_charge),
        percent=round(percent,1),
        selected_date=selected_date,
        balance=balance
    )

@app.route('/add', methods=['POST'])
def add():
    data.append({
        'date': request.form['date'],
        'id': request.form['id'],
        'name': request.form['name'],
        'amount': request.form['amount'],
        'method': request.form['method'],
        'type': request.form['type']
    })
    save()
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete():
    date = request.form['date']
    name = request.form['name']
    amount = request.form['amount']

    global data
    data = [
        i for i in data
        if not (
            i.get('date') == date and
            i.get('name') == name and
            str(i.get('amount')) == str(amount)
        )
    ]

    save()
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
