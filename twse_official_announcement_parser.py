
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


OFFICIAL_DOMAIN = "dsp.twse.com.tw"
BASE_URL = "https://dsp.twse.com.tw"


def parse_twse_announcements(html):
    """解析 TWSE 官方公告列表，不判定是否臨時停市。"""

    if not isinstance(html, str) or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    announcements = []

    for row in soup.select("table tr"):
        cells = row.find_all("td", recursive=False)

        # 略過表頭及非公告資料
        if len(cells) != 6:
            continue

        sequence = cells[0].get_text(" ", strip=True)

        if not sequence.isdigit():
            continue

        date = cells[1].get_text(" ", strip=True)
        recipient = cells[2].get_text(" ", strip=True)
        document_number = cells[3].get_text(" ", strip=True)
        subject = cells[4].get_text(" ", strip=True)

        attachments = []

        for link in cells[5].find_all("a", href=True):
            href = link["href"].strip()
            url = urljoin(BASE_URL, href)
            parsed = urlparse(url)

            # 僅接受 TWSE 官方網域的 PDF
            
            if (
                parsed.scheme != "https"
                or parsed.hostname != OFFICIAL_DOMAIN
                or parsed.port not in (None, 443)
                or parsed.username is not None
                or parsed.password is not None
                or not parsed.path.startswith(
                    "/public/static/downloads/announcement/official/"
                )
                or not parsed.path.lower().endswith(".pdf")
            ):
                continue


            attachments.append({
                "name": link.get_text(" ", strip=True),
                "url": url,
            })

        announcements.append({
            "sequence": int(sequence),
            "date": date,
            "recipient": recipient,
            "document_number": document_number,
            "subject": subject,
            "attachments": attachments,
            "source": "TWSE",
            "source_verified": False,
            "status": "UNKNOWN",
        })

    return announcements
