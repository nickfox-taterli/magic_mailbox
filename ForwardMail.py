import requests
import json
import base64
import sqlite3
import zlib
import time
from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# 参数设置(开始)

# testmail.app 密钥
TESTMAIL_APP_KEY = 'Bearer 04f245**-****-****-****-******cd8bd6'
# testmail.app 前缀
TESTMAIL_SURFIX = '*****'
# testmail.app 单次查询上限(只能大于0,太大会影速度,建议默认.)
TESTMAIL_LIMIT = 3
# SendGrid 已验证发送者邮箱
SENDGRID_MAIL_SENDER_ACCOUNT = '***********@stumail.sdut.edu.cn'
# SendGrid 密钥
SENDGRID_APP_KEY = 'Bearer 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'
# 邮件接收者邮箱(建议和发送者一样)
SENDGRID_MAIL_POST_ACCOUNT = '***********@stumail.sdut.edu.cn'

# 参数设置(结束)

client = Client(
    transport=RequestsHTTPTransport(
        url='https://api.testmail.app/api/graphql',
        headers={'Authorization': TESTMAIL_APP_KEY},
        use_json=True,
    ),
    fetch_schema_from_transport=True,
)

conn = sqlite3.connect('email.db')
c = conn.cursor()

query = gql('''
{
  inbox(namespace: "%s" limit:%d) {
    result
    message
    count
    emails {
      id
      tag
      timestamp
      subject
      html
      from
      from_parsed {
        address
        name
      }
      to
      to_parsed {
        address
        name
      }
      attachments {
        filename
        contentType
        checksum
        size
        headers {
          key
          line
        }
        downloadUrl
        contentId
        cid
        related
      }
      downloadUrl
    }
  }
}
''' % (TESTMAIL_SURFIX,TESTMAIL_LIMIT))

while True:
  # 查询邮件内容
  emails = client.execute(query)['inbox']['emails']
  # 如果有邮件内容,就会进入这个循环.
  for email in emails:
      # 转发模板
      msg = '''
              <pre>
              ---------- 原始信息 ---------
              发件人:%s[%s]
              发送时间:%s
              发送主题:%s
              目标邮箱:%s[%s]
              原始信息:%s
              </pre>
              %s
      ''' % (email['from_parsed'][0]['name'], email['from_parsed'][0]['address'], datetime.fromtimestamp(email['timestamp'] / 1000), email['subject'], email['to_parsed'][0]['name'], email['to_parsed'][0]['address'], email['downloadUrl'], email['html'])
      
      # 查询邮件是否已经转发过
      cursor = c.execute('SELECT * FROM email WHERE uuid = \'%s\'' % email['id'])
      
      # 如果没有转发过,就去转发.
      if cursor.fetchone() is None:
        
        # 构建发送的数据包
        payload = dict()
        payload['personalizations'] = [{'to': [{'email': SENDGRID_MAIL_POST_ACCOUNT}]}]
        payload['from'] = {'email': SENDGRID_MAIL_SENDER_ACCOUNT,'name':'Forwarding Robot'}
        payload['subject'] = email['subject']
        payload['content'] = [{'type': 'text/html', 'value': msg}]

        # 检查有没有附件,如果有附件,就需要把附件一起附加到发送内容中.
        if email['attachments']:
          payload['attachments'] = list()
          for attachment in email['attachments']:
              response = requests.get(attachment['downloadUrl'])
              payload['attachments'].append({'filename': attachment['filename'], 'type': attachment['contentType'], 'content': str(base64.b64encode(response.content),encoding = "utf-8")})

        # 为了日后复查和发送记录,邮件入库,并记录ID.
        response = requests.get(email['downloadUrl'])
        c.execute('INSERT INTO EMAIL (UUID,EML) VALUES (\'%s\', \'%s\')' % (email['id'],str(base64.b64encode(zlib.compress(response.content,9)),encoding = "utf-8")))
        conn.commit()
        
        print('邮件ID: %s 发送成功' % email['id'])

        # 通过SendGrid方式转发,免费版本每天可以转发100封邮件,学生版本每月可转发15000封邮件.
        response = requests.request("POST", "https://api.sendgrid.com/v3/mail/send", headers={'Content-Type': 'application/json','Authorization': SENDGRID_APP_KEY}, data=json.dumps(payload))

  time.sleep(1)

conn.close()