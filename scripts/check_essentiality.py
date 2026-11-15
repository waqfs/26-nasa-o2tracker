"""Verify sensor removal changes visible evidence, not the physical calculation."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8013');parser.add_argument('--output',default='outputs/local/essentiality-browser');args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(args.url);page.wait_for_function("document.querySelector('#physical-hypotheses').children.length===4&&document.querySelector('#ablation-rows').children.length===3")
    assert page.locator('.space-panel').is_visible()
    assert '127.881' in page.locator('#ablation-rows').inner_text()
    assert '0 oxygen-model parameters' in page.locator('#arm-verdict').inner_text()
    page.select_option('#evidence-arm','B')
    page.wait_for_function("document.querySelector('#arm-verdict').textContent.startsWith('Field + conventional satellites.')")
    assert page.locator('.space-panel').is_hidden() and page.locator('.without-nisar-panel').is_visible()
    assert page.locator('[data-evidence="radar"]').is_hidden()
    assert 'Sentinel-1' in page.locator('#withheld-evidence').inner_text()
    page.select_option('#evidence-arm','A')
    page.wait_for_function("document.querySelector('#physical-diagnostics').textContent.includes('L-band diagnostics are removed')")
    assert page.locator('[data-evidence="landsat"]').is_hidden()
    page.select_option('#evidence-arm','C')
    page.wait_for_function("document.querySelector('#physical-diagnostics').textContent.includes('OBSERVED')")
    page.locator('#essentiality').scroll_into_view_if_needed();page.screenshot(path=str(out/'essentiality-desktop.png'))
    page.locator('#calculate-flood').click();page.wait_for_function("!document.querySelector('#flood-output').hidden",timeout=30000)
    summary=page.locator('#flood-summary').inner_text();proof=page.locator('#live-arm-proof').inner_text();modelhash=proof.split('SHA-256 ')[1].split('.')[0]
    page.locator('#toggle-nisar').click();page.wait_for_function("document.querySelector('#live-arm-proof').textContent.startsWith('Arm B')")
    assert summary==page.locator('#flood-summary').inner_text()
    assert modelhash in page.locator('#live-arm-proof').inner_text()
    assert page.locator('.space-panel').is_hidden()
    page.locator('#reveal-flood').click();page.wait_for_function("!document.querySelector('#flood-reveal').hidden")
    assert '9.281 mg/L' in page.locator('#flood-reveal').inner_text()
    with page.expect_download() as event:page.locator('#export-flood').click()
    event.value.save_as(out/'arm-B-experiment.json');data=json.loads((out/'arm-B-experiment.json').read_text())
    assert data['result']['evidence_arm']=='B' and data['result']['model_output_sha256']==modelhash
    page.select_option('#measurement-question','oxygen')
    assert 'Current simulated' in page.locator('#measurement-plan').inner_text()
    page.locator('#flood-area').fill('150')
    assert 'Current simulated' not in page.locator('#measurement-plan').inner_text()
    page.select_option('#scenario-preset','disconnected')
    assert page.locator('#flood-connected').input_value()=='0' and page.locator('#flood-spread').input_value()=='0'
    assert page.locator('#flood-output').is_hidden()
    page.locator('#reset-flood').click();page.select_option('#evidence-arm','C')
    page.set_viewport_size({'width':390,'height':844});page.locator('#essentiality').scroll_into_view_if_needed();page.screenshot(path=str(out/'essentiality-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
checks=dict(arms=True,removed_measurements_hidden=True,frozen_default=True,unchanged_live_model_hash=True,explicit_reveal=True,range_specific_plan=True,stale_sensitivity_removed=True,disconnected_control=True,mobile_no_overflow=True,page_errors=errors)
(out/'checks.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks))
