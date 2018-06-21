# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

try:
    from urllib import parse
except:
    from urlparse import urlparse as parse
from bs4 import BeautifulSoup

from school_api.client.api.base import BaseSchoolApi
from school_api.client.api.utils.schedule_parse import ScheduleParse
from school_api.client.utils import ScheduleType


class Schedule(BaseSchoolApi):

    def _get_schedule(self, **kwargs):
        coding = 'gbk' if self.user_type else 'GB18030'
        res = self._get(self.schedule_url, **kwargs)
        if res.status_code != 200:
            return None
        schedule = ScheduleParse(res.content.decode(coding), self.schedule_type).get_schedule_dict()
        '''
        第一次请求的时候，教务系统默认返回最新课表
        如果设置了学年跟学期，匹配学年跟学期，不匹配则获取指定学年学期的课表
        '''
        if self.schedule_year and self.schedule_term:
            if self.schedule_year != schedule['schedule_year'] or \
                    self.schedule_term != schedule['schedule_term']:
                view_state = self._get_view_state_from_html(res.text)
                payload = {
                    '__VIEWSTATE': view_state,
                    ['xnd', 'xn'][self.schedule_type]: self.schedule_year,
                    ['xqd', 'xq'][self.schedule_type]: self.schedule_term
                }
                res = self._post(self.schedule_url, data=payload, **kwargs)

                if res.status_code != 200:
                    return None

                html = res.content.decode(coding)
                schedule = ScheduleParse(html, self.schedule_type).get_schedule_dict()

        return schedule

    def _get_schedule_payload(self, html, class_name):
        '''
        提取页面参数用于请求课表
        '''
        pre_soup = BeautifulSoup(html, "html.parser")
        schedule_view_state = pre_soup.find(attrs={"name": "__VIEWSTATE"})['value']
        schedule_id_list = pre_soup.find(id='kb').find_all('option')
        schedule_id = [name['value'] for name in schedule_id_list if name.text == class_name]
        # 获取班级课表
        payload = {
            '__VIEWSTATE': schedule_view_state,
            'kb': schedule_id
        }
        return payload

    def _get_schedule_by_bm(self, class_name, **kwargs):
        # 部门教师 查询学生班级课表  暂不做 学期学年 选择
        res = self._get(self.schedule_url, **kwargs)

        if res.status_code != 200:
            return None

        payload = self._get_schedule_payload(res.content.decode('gbk'), class_name)
        res = self._post(self.schedule_url, data=payload, **kwargs)

        if res.status_code != 200:
            return None

        html = res.content.decode('gbk')
        schedule = ScheduleParse(html, self.schedule_type).get_schedule_dict()

        return schedule

    def get_schedule(self, schedule_type=None, schedule_year=None, schedule_term=None, **kwargs):
        self.schedule_type = ScheduleType.CLASS if self.user_type \
            else schedule_type or ScheduleType.PERSON
        self.schedule_year = schedule_year
        self.schedule_term = schedule_term
        self.schedule_url = self.school_url["SCHEDULE_URL"][self.schedule_type]

        if self.user_type != 2:
            self.schedule_url += self.account
            data = self._get_schedule(**kwargs)
        else:
            self.schedule_url += parse.quote(self.account.encode('gb2312'))
            data = self._get_schedule_by_bm(**kwargs)

        return data
