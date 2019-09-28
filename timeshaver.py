from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.select import Select
from dataclasses import dataclass
import pandas as pd
import numpy as np
from enum import Enum


class AdpError(Exception):
    """Base exception for all TimeSaver exceptions.
    :param str message: a description of the exception
    """
    message = None

    def __init__(self, message=None):
        self.message = message or self.message
        super().__init__(self.message)
        
    
class AuthenticationError(AdpError):
    """Exception raised when an unauthorized access attempt has been made."""
    message = "The user attempted an unauthorized access to a resource."


@dataclass
class Credentials:
    uid: str
    passwd: str
    

class Periods(Enum):
    Current = "Current Period"
    Previous = "Previous Period"
    Next = "Next Period"
    Custom = "Date Range"

    
class TimeSaver:
    def __init__(self, version, key):
        # Create a headless browser
        options = Options()
        self.driver = webdriver.Firefox(options=options)
        self.service = ["https://timesaver.adphc.com",
                        version,
                        key,
                        'TS',
                        'login.php']
                             
        self.driver.get(self.base_url)
        self.credentials = None
        self._sites = None
        self._timetable = None
        self._totals = None
        self._periods = None

    def __del__(self):
        # Delete the headless browser
        self.driver.close()

    @property
    def base_url(self):
        return  '/'.join(self.service)
                             
    def authenticate(self):
        """Login to TimeSaver with the provided credentials."""
        uid_field = self.driver.find_element_by_id("username")
        passwd_field = self.driver.find_element_by_id("password")

        uid_field.send_keys(self.credentials.uid)
        passwd_field.send_keys(self.credentials.passwd)

        self.driver.find_element_by_id("bttSubmit").click()
        if not self.is_authenticated():
            raise AuthenticationError

    def logoff(self):
        """Log out of TimeSaver."""
        self.driver.find_element_by_id("logoffLinkImage").click()

    def punch(self):
        """Submit a new punch."""
        self.driver.find_element_by_id("bttAddPunch").click()

    def change_password(self, new_passwd):
        """Submit a password-change request."""
        self.driver.find_element_by_id("bttChangePassword").click()
        
        old_field = self.driver.find_element_by_id("FRMOldPassword")
        new_field = self.driver.find_element_by_id("FRMNewPassword")
        confirm_field = self.driver.find_element_by_id("FRMConfirmPassword")

        old_field.send_keys(self.credentials.passwd)
        new_field.send_keys(new_passwd)
        confirm_field.send_keys(new_passwd)

        self.driver.find_element_by_id("bttOk").click()

    @property
    def last_login(self):
        """Get the last successgul login time."""
        info = self.driver.find_element_by_xpath("//*[contains(text(), 'Last successful login')]")
        return info.text

    @property
    def approval_status(self):
        """Get approval status for the current period,
or return an empty string if no approval status can be found."""
        info = self.driver.find_element_by_id("spanTimePeriodApprovalStatus")
        return info.text

    @property
    def sites(self):
        if self._sites is None:
            self._sites = Select(self.driver.find_element_by_id("FRMTimestampSite"))
        return self._sites

    @property
    def site(self):
        """Return the currently selected work site."""
        return self.sites.all_selected_options[0].text

    @site.setter
    def site(self, idx):
        """Select a work site by index."""
        self.sites.select_by_index(idx)

    @property
    def sites_text(self):
        """Describe all available work sites."""
        return [option.text for option in self.sites.options]


    @property
    def timetable(self):
        if self._timetable is None:
            self.driver.find_element_by_id("anchorFolderTabs2").click()
            raw = self.driver.find_elements_by_xpath("//*[contains(@id, 'TimeEntriesRepeater')]")
            header = self.driver.find_elements_by_xpath("//*[@id='TimeEntriesHeader']/tr/th")
            
            columns = [
                column.text
                for column in header
            ]

            data = np.array([
                punch for punch in
                  [[element.text
                   for element in row.find_elements_by_xpath('td')]
                for row in raw]
                 if punch
            ])

            self._timetable = pd.DataFrame(data=data, columns=columns)

        return self._timetable

    @property
    def totals(self):
        """Return the total hours worked in the current period."""
        if self._totals is None:
            totals = self.driver.find_element_by_xpath(
                "//*[@id='TimeEntriesTotalTable']/tbody/tr[@id='trTotalWorked']"
            )
            
            self._totals = {
                "totalHours": totals.find_element_by_xpath("td[2]/p/span").text,
                "hourPayCodeTotal": totals.find_element_by_xpath("td[4]/p/span").text,
                "dollarPayCodeTotal": totals.find_element_by_xpath("td[6]/p/span").text,
                "projectTotal": totals.find_element_by_xpath("td[8]/p/span").text
            }

        return self._totals

    @property
    def periods(self):
        if self._periods is None:
            self._periods = Select(self.driver.find_element_by_id("FRMTimePeriod"))
        return self.periods

    @property
    def period(self):
        """Return the currently selected pay period."""
        return self.periods.all_selected_options[0].text

    @period.setter
    def site(self, *args):
        """Set the requested time period."""
        custom_fields = ["FRMFrom", "FRMTo"]
        
        if len(args) == 1:
            self.periods.select_by_visible_text(arg[0].value)
        elif len(args) == len(custom_fields):
            self.periods.select_by_visible_text(Periods.Custom.value)
            for i in len(custom_fields):
                field = self.driver.find_element_by_id(custom_fields[i])
            field.clear()
            field.send_keys(args[i].strftime("%x"))
        else:
            raise TypeError
            
    def is_authenticated(self):
        """Check that we have successfully authenticated."""
        try:
            header = self.driver.find_elements_by_css_selector("ADPUI-HeaderTitle")
        except:
            raise AuthenticationError

        raise NotImplementedError

    
        
