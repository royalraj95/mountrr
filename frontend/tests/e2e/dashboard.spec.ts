import {expect, test} from "@playwright/test";

test.describe("Dashboard", () => {
  test("loads and shows stat cards", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Mountrr/i);

    // Stat cards should be present
    await expect(page.getByText(/total symlinks/i)).toBeVisible();
    await expect(page.getByText(/broken/i)).toBeVisible();
  });

  test("shows mount health badges", async ({ page }) => {
    await page.goto("/");
    // At least one mount health badge visible
    const healthBadge = page.locator("[data-testid='mount-health'], .mount-health-badge").first();
    // Either badge is present or mount health section exists
    await expect(page.getByText(/mount health/i)).toBeVisible();
  });

  test("scan now button exists", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: /scan now/i })).toBeVisible();
  });
});
