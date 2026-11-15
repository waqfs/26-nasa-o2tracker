"""Browser QA for O2tracker in headless Microsoft Edge (Playwright): three viewports, real interactions, console errors,
horizontal overflow, and screenshots. Usage: python scripts/check_o2tracker.py [--url http://127.0.0.1:8010]"""
import argparse, json
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser(); ap.add_argument('--url', default='http://127.0.0.1:8010'); ap.add_argument('--output', default='outputs/local/o2tracker-qa')
a = ap.parse_args(); out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
report = []
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', headless=True)
    for name, vp, mobile in (('1440x900', {'width': 1440, 'height': 900}, False), ('1920x1080', {'width': 1920, 'height': 1080}, False), ('375x812', {'width': 375, 'height': 812}, True)):
        ctx = b.new_context(viewport=vp, is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1)
        pg = ctx.new_page(); errors = []
        pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errors.append(m.text))
        pg.goto(a.url + '/app#explore'); pg.wait_for_function("document.getElementById('map-loading').hidden === true && document.querySelectorAll('#timeline .tick').length > 0")
        r = {'viewport': name}
        r['first_screen'] = pg.evaluate("""() => { const c = document.getElementById('map').getBoundingClientRect(); return {canvas_visible: c.top < innerHeight && c.height > 250,
            title: document.title, heading: document.getElementById('explore-h').textContent, date: document.getElementById('stage-sub').textContent} }""")
        pg.screenshot(path=str(out / f'{name}-explore-compare.png'))
        # interactions: pick a pixel, switch layer, difference, single date via timeline
        box = pg.locator('#map').bounding_box(); pg.mouse.click(box['x'] + box['width'] * .4, box['y'] + box['height'] * .5)
        pg.wait_for_function("document.querySelector('#readout table') !== null")
        r['readout'] = pg.locator('#readout').inner_text()[:160]
        pg.get_by_role('radio', name='HV').click(); pg.wait_for_function("document.getElementById('map-loading').hidden")
        r['hv_legend'] = 'HV radar backscatter' in pg.locator('#legend').inner_text()
        pg.get_by_role('radio', name='Difference').click(); pg.wait_for_function("document.getElementById('map-loading').hidden")
        r['difference_legend'] = 'change' in pg.locator('#legend').inner_text()
        pg.screenshot(path=str(out / f'{name}-explore-difference.png'))
        pg.get_by_role('radio', name='Single date').click(); pg.locator('#timeline button.tick:not(.archive)').first.click(); pg.wait_for_function("document.getElementById('map-loading').hidden")
        r['single_date_label'] = pg.locator('#label-left').inner_text()
        pg.get_by_role('radio', name='Everglades').click(); pg.wait_for_function("document.getElementById('map-loading').hidden && document.getElementById('explore-h').textContent.includes('Everglades')")
        pg.get_by_role('radio', name='Phase').click(); pg.wait_for_function("document.getElementById('map-loading').hidden")
        r['phase_legend'] = 'phase' in pg.locator('#legend').inner_text().lower()
        pg.screenshot(path=str(out / f'{name}-explore-everglades.png'))
        r['overflow'] = {}
        for view in ('explore', 'evidence', 'context', 'about'):
            pg.evaluate(f"location.hash = '{view}'"); pg.wait_for_timeout(350)
            r['overflow'][view] = pg.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            if view != 'explore': pg.screenshot(path=str(out / f'{name}-{view}.png'), full_page=True)
        pg.evaluate("location.hash = 'evidence'"); pg.wait_for_timeout(200)
        pg.locator('#pair-seg input').nth(1).check(); r['pair_filter_points'] = pg.locator('#scatter circle').count()
        r['metrics'] = pg.locator('#metrics').inner_text().replace('\n', ' ')
        r['errors'] = errors; report.append(r); ctx.close()
    b.close()
(out / 'report.json').write_text(json.dumps(report, indent=1)); print(json.dumps(report, indent=1))
