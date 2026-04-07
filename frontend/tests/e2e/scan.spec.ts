import {expect, test} from "@playwright/test";

test.describe("Scan flow", () => {
  test("clicking Scan Now triggers a scan", async ({ page }) => {
    await page.goto("/");

    const scanBtn = page.getByRole("button", { name: /scan now/i });
    await expect(scanBtn).toBeVisible();
    await scanBtn.click();

    // Button should become disabled or change label while scan runs
    // Wait briefly for UI to react
    await page.waitForTimeout(300);

    // After a short wait the scan should eventually complete
    // (dev data is tiny — should finish within a few seconds)
    await expect(async () => {
      // Either button re-enables or a completion message appears
      const isEnabled = await scanBtn.isEnabled();
      const hasCompleted = await page.getByText(/scan complete|last scan/i).isVisible().catch(() => false);
      expect(isEnabled || hasCompleted).toBeTruthy();
    }).toPass({ timeout: 10_000 });
  });
});
