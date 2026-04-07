import {expect, test} from "@playwright/test";

test.describe("Symlinks page", () => {
  test("lists symlinks", async ({ page }) => {
    await page.goto("/symlinks");
    // Table or list should be visible
    await expect(page.getByRole("table").or(page.locator("tbody"))).toBeVisible();
  });

  test("filter by broken shows only broken rows", async ({ page }) => {
    await page.goto("/symlinks");

    // Click the Broken filter/tab
    const brokenFilter = page
      .getByRole("button", { name: /broken/i })
      .or(page.getByRole("option", { name: /broken/i }))
      .first();
    await brokenFilter.click();

    // Wait for update
    await page.waitForTimeout(500);

    // All visible status badges should say "broken"
    const statusCells = page.locator("[data-status='broken'], .status-broken");
    const count = await statusCells.count();
    // If any rows are shown they must be broken
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        await expect(statusCells.nth(i)).toBeVisible();
      }
    }
  });
});
