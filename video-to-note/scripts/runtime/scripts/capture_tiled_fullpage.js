async (page) => {
  const targetUrl = page.url();
  const match = targetUrl.match(/\/outputs\/([^/]+)\/html\//);
  if (!match) {
    throw new Error("Open an outputs/<video-id>/html page before capturing tiles");
  }
  const outputDir = `outputs/${match[1]}/render-check/tiles`;
  const viewportHeight = 1600;

  await page.setViewportSize({ width: 1440, height: viewportHeight });
  await page.goto(targetUrl, { waitUntil: "networkidle" });
  const fullHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const maxScroll = Math.max(0, fullHeight - viewportHeight);
  const positions = [];
  for (let y = 0; y < maxScroll; y += viewportHeight) {
    positions.push(y);
  }
  if (!positions.length || positions[positions.length - 1] !== maxScroll) {
    positions.push(maxScroll);
  }

  for (let index = 0; index < positions.length; index += 1) {
    const y = positions[index];
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await page.screenshot({
      path: `${outputDir}/tile_${String(index + 1).padStart(3, "0")}.png`,
      fullPage: false,
      animations: "disabled",
    });
  }

  return { width: 1440, fullHeight, viewportHeight, positions };
}
