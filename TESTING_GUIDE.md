# Cross-Browser Testing Guide

## Quick Test Checklist

### Before Testing
1. Start the server: `python server.py`
2. Open browser to: `http://localhost:5000`
3. Open browser developer tools (F12)

---

## Test on Each Browser

### ✅ Chrome (Recommended for Development)

**Versions to Test**: Chrome 120+

**Test Steps**:
1. [ ] Page loads without errors (check Console)
2. [ ] All sections navigate correctly
3. [ ] Dark mode toggle works
4. [ ] Charts render (Plotly & Chart.js)
5. [ ] AI Token Stats page displays data
6. [ ] Code Analyzer form works
7. [ ] Sidebar toggle responsive

**DevTools Tips**:
- F12 → Console: Check for JavaScript errors
- F12 → Network: Check API calls
- F12 → Application → LocalStorage: Check theme persistence

---

### ✅ Firefox

**Versions to Test**: Firefox 121+

**Test Steps**:
1. [ ] Page loads without errors
2. [ ] CSS Grid layouts render correctly
3. [ ] Charts display properly
4. [ ] Fetch API calls work
5. [ ] LocalStorage persists

**Known Issues**:
- None currently

**DevTools Tips**:
- F12 → Console: Check errors
- F12 → Storage → Local Storage: Check theme

---

### ✅ Safari (macOS/iOS)

**Versions to Test**: Safari 17+

**Test Steps**:
1. [ ] Page loads without errors
2. [ ] CSS Grid gaps render correctly
3. [ ] Charts render (may need refresh)
4. [ ] Dark mode works
5. [ ] Mobile responsive (iOS)

**Known Issues**:
- Older Safari (12-13) may have CSS Grid rendering issues
- Solution: Update to Safari 14+

**DevTools Tips**:
- Safari → Develop → Show Web Inspector
- Check Console for errors

---

### ✅ Edge (Chromium)

**Versions to Test**: Edge 120+

**Test Steps**:
1. [ ] Same as Chrome (same engine)
2. [ ] Verify no Edge-specific issues

**Known Issues**:
- None (uses Chromium engine)

---

### ✅ Mobile Browsers

#### iOS Safari
1. [ ] Responsive layout works
2. [ ] Touch interactions smooth
3. [ ] Charts render correctly
4. [ ] Sidebar toggle works on mobile

#### Android Chrome
1. [ ] Responsive layout works
2. [ ] Touch interactions smooth
3. [ ] Charts render correctly
4. [ ] Sidebar toggle works on mobile

---

## Feature-Specific Testing

### 1. Navigation & Routing

**Test in all browsers**:
```
Dashboard → New Review → History → Statistics → AI Stats → Code Analyzer
```

**Expected**:
- URL hash updates: `#dashboard`, `#new-review`, etc.
- Only active section visible
- Active nav item highlighted
- Page title updates

---

### 2. Theme Toggle

**Test Steps**:
1. Click theme toggle (sun/moon icon in header)
2. Page switches to dark mode
3. Refresh page
4. Dark mode persists
5. Navigate to different section
6. Theme stays consistent

**Check**:
- [ ] localStorage saves theme
- [ ] CSS variables update
- [ ] Charts adapt to theme
- [ ] All sections respect theme

---

### 3. Dashboard Charts

**Test in each browser**:
1. Go to Dashboard
2. Verify all Plotly charts render:
   - Issues Over Time
   - Issues by Repository
   - DDD Score Trend
   - Test Coverage Trend
   - Review Complexity Analysis (bubble chart)

**Expected**:
- Charts render without errors
- Interactive hover tooltips work
- Responsive on window resize

---

### 4. AI Token Stats

**Test Steps**:
1. Click "AI Token Stats" in sidebar
2. Wait for data to load
3. Verify:
   - [ ] Summary cards show numbers
   - [ ] Token Distribution chart (Chart.js)
   - [ ] Token Trend chart (Chart.js)
   - [ ] Detailed table populates

**Console Output Should Show**:
```
Loading AI Token Stats...
AI Stats App initializing...
Loading summary stats...
Stats: X reviews, Y tokens, Z avg
Elements found: {aiStatsReviewCount: true, ...}
```

---

### 5. Code Analyzer

**Test Steps**:
1. Click "Code Analyzer" in sidebar
2. Fill form:
   - Repo URL: `https://github.com/user/repo.git`
   - Branch: `main`
   - Toggle options
3. Submit form
4. Verify progress bar updates
5. Check results display

---

### 6. API Integration

**Test API Calls** (Network tab):

Expected successful calls:
- `GET /health` → 200 OK
- `GET /api/sessions` → 200 OK (with data)
- `GET /api/sessions/token-stats` → 200 OK
- `GET /api/prompt-versions` → 200 OK
- `POST /api/review` → 200 OK (when starting review)

---

## Common Issues & Solutions

### Issue: Charts Not Rendering

**Symptoms**: Blank white/gray areas where charts should be

**Debug Steps**:
1. Open Console (F12)
2. Look for errors mentioning Plotly or Chart.js
3. Check Network tab for failed CDN loads

**Solutions**:
- Verify CDN links are working
- Check if ad blocker is blocking CDNs
- Try in incognito/private mode
- Clear cache and hard refresh (Ctrl+Shift+R)

---

### Issue: Dark Mode Not Working

**Symptoms**: Theme toggle doesn't change appearance

**Debug Steps**:
1. Check Console for JavaScript errors
2. Check localStorage in DevTools:
   - Application → Storage → Local Storage
   - Look for `theme` key

**Solutions**:
- Clear localStorage: `localStorage.clear()`
- Refresh page
- Check if JavaScript is enabled
- Try different browser

---

### Issue: Data Not Loading

**Symptoms**: Sections show "Loading..." forever

**Debug Steps**:
1. Check Console for fetch errors
2. Check Network tab for failed API calls
3. Verify server is running on port 5000

**Solutions**:
- Restart server: `python server.py`
- Check MongoDB is running
- Check API endpoint logs
- Try different browser to isolate issue

---

### Issue: Sidebar Not Toggling

**Symptoms**: Clicking sidebar toggle does nothing

**Debug Steps**:
1. Check Console for JavaScript errors
2. Verify event listener attached

**Solutions**:
- Hard refresh (Ctrl+Shift+R)
- Check if `app.js` loaded successfully
- Try different browser

---

## Performance Testing

### Chrome DevTools Lighthouse

1. Open DevTools (F12)
2. Go to "Lighthouse" tab
3. Select categories:
   - ✅ Performance
   - ✅ Accessibility
   - ✅ Best Practices
4. Click "Analyze page load"

**Target Scores**:
- Performance: 90+
- Accessibility: 90+
- Best Practices: 95+

---

## Automated Testing (Optional)

### Using Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

# Test in Chrome
driver = webdriver.Chrome()
driver.get('http://localhost:5000')

# Test navigation
dashboard = driver.find_element(By.CSS_SELECTOR, 'a[data-section="dashboard"]')
dashboard.click()

# Test theme toggle
theme_btn = driver.find_element(By.ID, 'themeToggle')
theme_btn.click()

driver.quit()
```

---

## Browser Testing Matrix

| Feature | Chrome | Firefox | Safari | Edge | Mobile |
|---------|--------|---------|--------|------|--------|
| Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| New Review | ✅ | ✅ | ✅ | ✅ | ✅ |
| History | ✅ | ✅ | ✅ | ✅ | ✅ |
| Statistics | ✅ | ✅ | ✅ | ✅ | ✅ |
| AI Stats | ✅ | ✅ | ✅ | ✅ | ✅ |
| Code Analyzer | ✅ | ✅ | ✅ | ✅ | ✅ |
| Dark Mode | ✅ | ✅ | ✅ | ✅ | ✅ |
| Plotly Charts | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Chart.js | ✅ | ✅ | ✅ | ✅ | ⚠️ |

⚠️ = May need larger screen for full experience

---

## Reporting Issues

When reporting a browser-specific issue, include:

1. **Browser**: Name and version (e.g., "Chrome 120.0.6099.109")
2. **OS**: Operating system (e.g., "Windows 11", "macOS 14.1")
3. **Steps to Reproduce**: Exact steps that cause the issue
4. **Expected**: What should happen
5. **Actual**: What actually happened
6. **Console Errors**: Any JavaScript errors from Console
7. **Screenshot**: If visual issue

**Example**:
```
Browser: Firefox 121.0 on Windows 11
Steps: 1. Click "AI Token Stats" 2. Wait 5 seconds
Expected: Charts render
Actual: Blank white areas
Console: TypeError: Cannot read property 'getContext' of null
```

---

## Test Report Template

```markdown
## Browser Test Report - [Date]

**Tested By**: [Your Name]
**Build Version**: [Git commit hash]

### Chrome 120+ ✅
- All features working
- No console errors
- Performance: 95/100

### Firefox 121+ ✅
- All features working
- No console errors
- Performance: 93/100

### Safari 17+ ✅
- All features working
- Minor CSS rendering delay
- Performance: 91/100

### Edge 120+ ✅
- All features working
- No console errors
- Performance: 95/100

### Issues Found
- None

### Recommendations
- None
```

---

## Continuous Testing

### Development Workflow

1. **Before Commit**: Test in Chrome
2. **Before PR**: Test in Chrome + Firefox
3. **Before Release**: Test all browsers
4. **After Release**: Monitor error tracking

### Browser Version Updates

Check quarterly:
- Chrome: https://chromereleases.googleblog.com/
- Firefox: https://www.mozilla.org/firefox/releasenotes/
- Safari: https://developer.apple.com/safari/
- Edge: https://docs.microsoft.com/en-us/deployedge/

---

## Additional Resources

- **Can I Use**: https://caniuse.com/ - Check feature support
- **BrowserStack**: https://www.browserstack.com/ - Cross-browser testing
- **MDN Compat Data**: https://github.com/mdn/browser-compat-data

---

*Last Updated: 2024-12-26*
