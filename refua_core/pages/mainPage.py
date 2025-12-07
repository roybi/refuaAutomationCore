from playwright.sync_api import Page

class MainPage:
  def __init__(self, page: Page):
    self.__myRequsetsButton = page.locator("data-test-id=my-requests-button")
    
    