import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await (await b.new_context(viewport={'width':390,'height':844})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8799/index.html')
        await pg.wait_for_timeout(2000)
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        ver = await pg.evaluate("APP_VERSION")
        print("version:", ver)
        yard_html = await pg.evaluate("bpRoomIconHtml('Yard / Grading', 'Exterior')")
        print("Yard/Grading icon html:", yard_html[:80], '...')
        front_yard = await pg.evaluate("bpRoomIconHtml('Front Yard', 'Exterior')")
        print("Front Yard icon html matches:", 'data-v380' in front_yard)
        # make sure other icons unaffected
        kitchen = await pg.evaluate("bpRoomIconHtml('Kitchen', 'Kitchen')")
        print("Kitchen icon still has 'kitchen' label:", 'kitchen' in kitchen)
        driveway = await pg.evaluate("bpRoomIconHtml('Driveway', 'Exterior')")
        print("Driveway icon still has data-v328:", 'data-v328' in driveway)
        print("page errors:", errs)
        await b.close()

asyncio.run(main())
