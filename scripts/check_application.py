"""Exercise the normal UI in fresh desktop and mobile browser contexts."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8010')
parser.add_argument('--output',default='outputs/local/browser')
args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
checks=[]
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(channel='msedge',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1000})
    page=context.new_page();errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    start=time.monotonic();page.goto(args.url+'/investigation')
    page.wait_for_function("document.querySelector('#aligned-rows').children.length===3")
    page.wait_for_function("document.querySelector('#simulation-summary').textContent.includes('MODELED')")
    checks.append(dict(load_seconds=round(time.monotonic()-start,2)))
    assert page.locator('#area option').count()==26
    assert page.locator('#station option').count()==2
    assert page.locator('#association-status').inner_text()=='INSUFFICIENT DATA'
    page.screenshot(path=str(out/'oxygen-desktop.png'))
    for scene in range(8):
        page.locator(f'[data-scene="{scene}"]').click()
        assert page.locator('#story-title').inner_text()
    page.select_option('#pass','1')
    page.locator('#reveal').click()
    page.wait_for_function("document.querySelector('#oxygen-reveal').textContent.includes('Measured oxygen')")
    assert '9.281 mg/L' in page.locator('#oxygen-reveal').inner_text()
    page.locator('#reveal-result').screenshot(path=str(out/'observed-oxygen.png'))
    page.select_option('#station','A4261053')
    page.wait_for_function("document.querySelector('#do-range').textContent.includes('Awaiting reveal')")
    page.select_option('#variable','level')
    page.wait_for_function("document.querySelector('#aligned-rows').textContent.includes('GOOD')")
    page.select_option('#station','A4261108')
    page.wait_for_function("document.querySelector('#variable-note').textContent.includes('no retained')")
    page.select_option('#variable','oxygen')
    page.locator('#lag').fill('3');page.locator('#lag').dispatch_event('change')
    page.select_option('#mode','as_of')
    page.wait_for_function("document.querySelector('#aligned-rows').textContent.includes('FUTURE DATA BLOCKED')")
    page.select_option('#mode','retrospective')
    page.locator('#lag').fill('0');page.locator('#lag').dispatch_event('change')
    page.wait_for_function("document.querySelector('#aligned-rows').textContent.includes('GOOD')")
    page.locator('#reveal').click()
    page.wait_for_function("!document.querySelector('#export').disabled")
    with page.expect_download() as event:page.locator('#export').click()
    event.value.save_as(out/'investigation.json')
    data=json.loads((out/'investigation.json').read_text())
    assert data['comparison']['statistics']['pearson'] is None
    page.locator('#legacy-model > summary').click()
    before=page.locator('#simulation-summary').inner_text()
    page.locator('#sim-demand').fill('30');page.locator('#run-simulation').click()
    page.wait_for_function("document.querySelector('#simulation-summary').textContent!=="+json.dumps(before))
    page.select_option('#polarization','HVHV')
    page.wait_for_function("document.querySelector('#mesh-layer').value==='HV_20260928'")
    page.locator('#signal-canvas').screenshot(path=str(out/'oxygen-terrain.png'))
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#workspace').scroll_into_view_if_needed()
    page.screenshot(path=str(out/'oxygen-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    checks.append(dict(stations=True,variables=True,lag_and_future_gate=True,report_export=True,
                       modeled_controls=True,polarizations=True,mobile_no_overflow=True,page_errors=errors))
    context.close();browser.close()
(out/'checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks))
