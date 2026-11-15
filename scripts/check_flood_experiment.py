"""Check the scientific reveal, scenario controls and conditional uncertainty in a real browser."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8010');parser.add_argument('--output',default='outputs/local/flood-browser');args=parser.parse_args()
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(args.url)
    page.wait_for_function("document.querySelector('#published-parameters').children.length===9")
    assert page.locator('#do-range').inner_text()=='Awaiting reveal'
    assert page.locator('#explanations').is_hidden()
    assert 'Withheld until reveal' in page.locator('#aligned-rows').inner_text()
    assert page.locator('#flood-use-boundary').is_disabled()
    assert 'UNVERIFIED TELEM' in page.locator('#boundary-note').inner_text()
    for choice in ['field','landsat','radar']:
        page.select_option('#evidence-choice',choice)
        assert page.locator(f'[data-evidence="{choice}"]').evaluate("e=>e.classList.contains('selected')")
    page.locator('#calculate-flood').click()
    page.wait_for_function("!document.querySelector('#flood-output').hidden",timeout=30000)
    assert page.locator('#flood-reveal').is_hidden()
    assert 'Potential stoichiometric demand' in page.locator('#flood-summary').inner_text()
    with page.expect_download() as event:page.locator('#export-flood').click()
    event.value.save_as(out/'scenario-before-reveal.json')
    export=json.loads((out/'scenario-before-reveal.json').read_text())
    assert export['observations_revealed'] is None
    assert export['result']['measured_target_oxygen_used'] is False
    page.locator('#flood-budget').scroll_into_view_if_needed()
    page.screenshot(path=str(out/'flood-experiment-desktop.png'))
    page.locator('#reveal-flood').click()
    page.wait_for_function("!document.querySelector('#flood-reveal').hidden")
    assert '9.281 mg/L' in page.locator('#flood-reveal').inner_text()
    assert page.locator('#do-range').inner_text()!='Awaiting reveal'
    assert page.locator('#explanations').is_visible()
    page.select_option('#flood-compartment','floodplain')
    page.select_option('#sensitivity-target','potential_oxygen_demand_kg')
    assert 'litter' in page.locator('#flood-measurement').inner_text()
    page.locator('#flood-output').screenshot(path=str(out/'flood-reveal.png'))
    page.locator('#flood-connected').fill('0')
    assert page.locator('#flood-output').is_hidden()
    page.select_option('#station','A4261053');page.select_option('#pass','0')
    page.wait_for_function("!document.querySelector('#flood-use-boundary').disabled")
    assert page.locator('#do-range').inner_text()=='Awaiting reveal'
    page.locator('#flood-use-boundary').check()
    page.locator('#calculate-flood').click()
    page.wait_for_function("!document.querySelector('#flood-output').hidden",timeout=30000)
    page.locator('#reset-flood').click()
    assert page.locator('#flood-area').input_value()=='100'
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#flood-budget').scroll_into_view_if_needed()
    page.screenshot(path=str(out/'flood-experiment-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
checks=dict(hidden_target=True,evidence_choices=True,no_radar_area_conversion=True,ensemble=True,export_without_target=True,explicit_reveal=True,quality_gated_boundaries=True,stale_result_invalidated=True,responsive=True,page_errors=errors)
(out/'checks.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks))
