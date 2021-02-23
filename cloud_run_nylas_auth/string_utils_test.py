import unittest


class TestCampaignPerf(unittest.TestCase):
    def test_html_replace(self):
        html = """\
            <html>
              <body>
                <p>Hi, $(name)<br>
                   <span> $(error) </span><br>
                </p>
              </body>
            </html>
        """
        html = html.replace("$(name)", "John")
        html = html.replace("$(error)", "Something went wrong!")
        print(html)

if __name__ == '__main__':
    unittest.main()
