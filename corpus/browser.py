"""Normal browser fallback for public pages, with no challenge or login bypass."""
import html
import re
import time

from corpus.access import CHALLENGES, GATES, public_text
from news_scrapper.extract_content import ExtractionFailure, utc_now


def rendered_article_html(title, visible):
    return '<html><head><meta charset="utf-8"><title>'+html.escape(title)+'</title></head><body><article>' + ''.join(
        '<p>'+html.escape(line.strip())+'</p>' for line in visible.splitlines() if line.strip()) + '</article></body></html>'


def browser_extract(browser, url, permission):
    context = browser.new_context()
    page = context.new_page()
    blocked = []

    def route_main(route):
        if route.request.is_navigation_request() and route.request.frame == page.main_frame:
            try:
                wait = permission(route.request.url)
                origin = route.request.url.split('/',3)[:3]
                origin = '/'.join(origin)
                remaining = wait - (time.monotonic()-last_navigation.get(origin,0))
                if remaining>0:
                    time.sleep(remaining)
                last_navigation[origin] = time.monotonic()
            except Exception as exc:
                blocked.append(str(exc))
                route.abort()
                return
        route.continue_()

    last_navigation = {}
    page.route('**/*',route_main)
    result = {'url':url,'extracted_at':utc_now(),'article_text':None,'extraction_error':None,'http_status':None}
    try:
        permission(url)
        response = page.goto(url,wait_until='domcontentloaded',timeout=25000)
        result['http_status'] = response.status if response else None
        if response and response.status != 200:
            raise ExtractionFailure(f'browser_http_{response.status}')
        page.wait_for_timeout(1500)
        text = page.locator('body').inner_text(timeout=5000)
        if CHALLENGES.search(text):
            raise ExtractionFailure('browser_challenge')
        # Dismiss ordinary consent UI only. Never interact with login, payment,
        # CAPTCHA, verification widgets, or restricted article controls.
        for label in (r'^reject all$',r'^reject optional cookies$',r'^accept all cookies$'):
            button = page.get_by_role('button',name=re.compile(label,re.I))
            if button.count()==1 and button.is_visible():
                button.click(timeout=2000)
                page.wait_for_timeout(500)
                break
        candidates = page.locator('article, [itemprop="articleBody"], main, .entry-content, .post-content, .article-content')
        texts = []
        for i in range(candidates.count()):
            if candidates.nth(i).is_visible():
                texts.append(candidates.nth(i).inner_text())
        if not texts:
            raise ExtractionFailure('no_visible_article_container')
        visible = max(texts,key=len)
        if GATES.search(visible):
            raise ExtractionFailure('subscription_gate')
        body = rendered_article_html(page.title(),visible)
        article_text, method, _ = public_text(body,page.url)
        result.update(article_text=article_text,method='browser_visible_text',resolved_url=page.url,word_count=len(article_text.split()))
    except Exception as exc:
        result['extraction_error'] = blocked[0] if blocked else str(exc) if isinstance(exc,ExtractionFailure) else type(exc).__name__
    finally:
        context.close()
    return result
