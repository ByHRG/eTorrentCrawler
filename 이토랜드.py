from bs4 import BeautifulSoup
import requests
import time
from datetime import datetime
from urllib import parse

# 현재 CSV파일로 저장. 추후에 DB로 저장하게 되면 변경
import pandas as pd
#import pymongo
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

'''
 crawler
 각 사이트마다 검색조건을 통해 게시물을 수집함
 ex) keyword = '강아지', site = 다음 블로그, startDate(수집시작일) = 2021-01-01, endDate(수집종료일) = 2021-04-20 
    ---> 다음블로그에서 2021-01-01 ~ 2021-04-20 기간 사이의 "강아지"가 들어간 게시물을 모두 수집하는 조건
    ---> 검색조건에 따라 url설정
'''
class Crawler:
    def __init__(self):
        self.keyword = '쇼미' #수집 키워드
        self.site = '이토랜드' # 수집 사이트
        self.startDate = '' #수집 시작일
        self.endDate = '' #수집 종료일
        self.url = 'http://www.etoland.co.kr/bbs/new1.php?gr_id=bbs&view=&mb_id=&subject={keyword}&ext_search=1&page={page}' # 수집할 게시물리스트(게시판) url (검색조건(keyword, site, startDate, endDate)에 따라 설정)
        self.postUrls = []  # 게시판에서 게시물 url들을 담아 리턴할 리스트

    # 데이터에서 html tag 제외
    def delrn(self, text):
        return text.replace("\t","").replace("\n","").replace("\r","").lstrip().rstrip()

    def enco(self, text):
        return parse.quote(text, encoding='EUC-KR')

    def getList(self)-> list:

        '''
         --- 1페이지부터 <사이트마다 page 파라미터 확인>
        '''
        page = 0
        while True:
            page = page+1
            req = requests.get(self.url.format(page=page,keyword=self.enco(self.keyword)), verify=False)
            print('[ * ] page -> '+ str(page) )
            req.encoding='EUC-KR'
            soup = BeautifulSoup(req.text, "html.parser")

            # 게시물 리스트 url 가져오기 <사이트마다 태그변경 또는 소스코드 수정 필요>

            if len(soup.findAll('td',{'class':'list_subject'}))==0:break
            for a in soup.findAll('td',{'class':'list_subject'}):
                postInfor = {
                            'url': "http://www.etoland.co.kr/bbs"+a.find('a')['href'][1:],
                            'crawled':False, # getPost()에서 해당url에서 게시물 상세정보를 가져왔는지 확인할 플래그,
                            }
                            
                # 수집되지 않은 url이면 append
                exist = next((item for item in self.postUrls if item['url'] == postInfor['url']), None)
                if type(exist) != dict: self.postUrls.append(postInfor)
                else:break
                print(postInfor)
        
        print('[ - ] lenPostUrls = ', len(self.postUrls))

    def getPost(self)-> list:
        # 게시물 상세정보 수집 
        for post in self.postUrls:
            req = requests.get(post['url'], verify=False)
            req.encoding='EUC-KR'
            print('[ * ] post req -> '+post['url'])
            soup = BeautifulSoup(req.text, 'html.parser')


            # --- 게시물의 제목/내용/작성자아이디/작성자닉네임/작성일자 등을 가져옴 <사이트마다 태그변경 또는 소스코드 수정 필요>
            post['title'] = self.delrn(soup.find('td',{'class':'mw_basic_view_subject'}).find('h1').text)
            try:
                post['Content'] = self.delrn(soup.find("div",{"id":"view_content"}).text)
            except:
                post['Content'] = ''
            post['userid'] = str(soup.find('span',{'class':'mw_basic_view_name'}).find("a")).split("this, '")[1].split("', ")[0]
            post['username'] = soup.find("span",{"class":"member"}).text
            post['datePublished'] = soup.find("span",{"class":"mw_basic_view_datetime"}).text.split('(')[0]+soup.find("span",{"class":"mw_basic_view_datetime"}).text.split(') ')[1]
            post['dateScraped'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 이미지가 있다면
            post['img'] = []
            for img in soup.find('td',{'class':'mw_basic_view_content'}).findAll('img'):
                if img["src"][0] == "/":
                    post['img'].append("https://www.etoland.co.kr"+img["src"])
                elif img["src"][0] == "h":
                    post['img'].append(img["src"])
                elif img["src"][0] == ".":
                    post['img'].append("https://www.etoland.co.kr"+img["src"][2:])


            # like(좋아요수) / hate(싫어요수) / reply(댓글수) / thumbnail(썸네일) 이 존재하면 수집

            # ---댓글을 수집해야하는 사이트면
            post['CmtCnt'] = None
            post['Comments'] = []
            
            cmtlist = soup.find('div',{'id':'commentContents'})
            replycounter = 0
            cmtnum = 1
            #사이트마다 댓글 html형식에 따라 소스수정soup
            CommentList = cmtlist.findAll('table')
            for n in CommentList:
                try:
                    if cmtnum>=len(CommentList):break
                    n = CommentList[cmtnum]
                    try:
                        content = self.delrn(n.find('textarea').text)
                    except:
                        content = self.delrn(n.findAll('div')[1].text)
                    # --- 댓글의 내용/작성자아이디/작성자닉네임/작성일자 등을 가져옴 <사이트마다 태그변경 또는 소스코드 수정 필요>
                    commentInfor = {'userid': n.find('span',{'class':'mw_basic_comment_name'}).find('a')['onclick'].split("this, '")[1].split("',")[0],
                                    'username': n.find('span',{'class':'member'}).text,
                                    'datePublished': n.find('span',{'mw_basic_comment_datetime'}).text.split(' (')[0]+n.find('span',{'mw_basic_comment_datetime'}).text.split(')')[1],
                                    'Content': content,
                                    'like':int(n.find('span',{'mw_basic_comment_good'}).find('span').text),
                                    'hate':int(n.find('span',{'mw_basic_comment_nogood'}).find('span').text),
                                    'reCmtCnt' : None,
                                    'reComments':[]
                                }
                    reCommentscounter = 0
                    while True:
                        if cmtnum+4>=len(CommentList):break
                        nn = CommentList[cmtnum+4]
                        try:
                            rcontent = self.delrn(nn.find('textarea').text)
                        except:
                            rcontent = self.delrn(nn.findAll('div')[1].text)
                        try:
                            nn.find('img',{'title':'코멘트리플'})['align']
                            reComments = {'userid': nn.find('span',{'class':'mw_basic_comment_name'}).find('a')['onclick'].split("this, '")[1].split("',")[0],
                                            'username': nn.find('span',{'class':'member'}).text,
                                            'datePublished': nn.find('span',{'mw_basic_comment_datetime'}).text.split(' (')[0]+nn.find('span',{'mw_basic_comment_datetime'}).text.split(')')[1],
                                            'Content': rcontent,
                                            'like':int(nn.find('span',{'mw_basic_comment_good'}).find('span').text),
                                            'hate':int(nn.find('span',{'mw_basic_comment_nogood'}).find('span').text)
                                        }
                            commentInfor['reComments'].append(reComments)
                            cmtnum = cmtnum+4
                            replycounter = replycounter+1
                            reCommentscounter=reCommentscounter+1
                        except:break
                    cmtnum = cmtnum+4
                    replycounter = replycounter+1
                    commentInfor['reCmtCnt'] = reCommentscounter
                    post['Comments'].append(commentInfor)
                except:
                    cmtnum = cmtnum+4
            # ---
            post['CmtCnt'] = replycounter
            # 해당 url 게시물 크롤링 완료
            post['crawled'] = True

       

    def getCSV(self):
        today = datetime.now().now().strftime("%Y%m%d%H%M")
        pd.DataFrame(self.postUrls).to_csv("cwaling/"+today+self.keyword+"_"+self.site+".csv", encoding='utf-8-sig')
        print('[ * ] getCSV terminated')


if __name__=="__main__":   
    # 크롤러
    c = Crawler()

    # getList -> list (게시물 url 수집)
    c.getList()

    # getPost-> list (게시물 url로부터 게시물 상세정보 수집)
    c.getPost()

    # CSV로 출력
    c.getCSV()