/* ═══════════════════════════════════════════════════════════
   The Copper Spoon — Restaurant Agent (app.js)
   Handles chat, menu, reservations, orders, feedback,
   dark mode, tabs, PWA, and admin auth.
   ═══════════════════════════════════════════════════════════ */

(() => {
  "use strict";

  // ── State ──────────────────────────────────────────────

  const getInitialData = (id) => {
    try {
      const el = document.getElementById(id);
      return el ? JSON.parse(el.textContent) : null;
    } catch (e) {
      console.warn(`Failed to parse initial data: ${id}`, e);
      return null;
    }
  };

  const profile = getInitialData("initial-profile") || {};
  let menuState = getInitialData("initial-menu");
  let activeChatRequest = null;
  let feedbackRating = 0;
  let orderCart = JSON.parse(localStorage.getItem("orderCart") || "[]");
  let deferredInstallPrompt = null;
  let isAdmin = document.body.dataset.isAdmin === "true";
  let hasInitialized = false;
  let isTogglingPortal = false;
  let revealObserver = null;
  const expandedSections = new Set();

  // ── DOM References ─────────────────────────────────────

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  const chatLog = $("[data-chat-log]");
  const chatForm = $("[data-chat-form]");
  const chatInput = $("#chat-message");
  const menuGrid = $("[data-menu-grid]");
  const menuSearchInput = $("#menu-search");
  const refreshMenuButton = $("[data-refresh-menu]");
  const resetChatButton = $("[data-reset-chat]");
  const reservationForm = $("[data-reservation-form]");
  const reservationStatus = $("[data-reservation-status]");
  const feedbackForm = $("[data-feedback-form]");
  const feedbackStatus = $("[data-feedback-status]");
  const feedbackReviews = $("[data-feedback-reviews]");
  const feedbackStatsEl = $("[data-feedback-stats]");
  const orderItemsList = $("[data-order-items]");
  const orderTotalEl = $("[data-order-total]");
  const orderForm = $("[data-order-form]");
  const orderStatus = $("[data-order-status]");
  const orderLookupInput = $("#order-lookup-input");
  const orderLookupBtn = $("[data-order-lookup]");
  const orderResultEl = $("[data-order-result]");
  const orderItemsDrawer = $("[data-order-items-drawer]");
  const orderTotalDrawer = $("[data-order-total-drawer]");
  
  const resAvailBar = $("[data-availability-bar]");
  const resAvailText = $("[data-avail-text]");
  const resAvailFill = $("[data-avail-fill]");
  const resDateInput = $("[data-avail-date]");
  const resTimeInput = $("[data-avail-time]");
  const resLookupInput = $("#reservation-lookup-input");
  const resLookupBtn = $("[data-reservation-lookup]");
  const resResultEl = $("[data-reservation-result]");
  
  const themeToggle = $("[data-theme-toggle]");
  const adminToggle = $("[data-admin-toggle]");
  const adminModal = $("[data-admin-modal]");
  const adminLoginForm = $("[data-admin-login-form]");
  const adminCloseBtn = $("[data-admin-close]");
  const installBanner = $("[data-install-banner]");

  const chatFab = $("[data-chat-fab]");
  const chatWidget = $("[data-chat-widget]");
  const chatCloseBtn = $("[data-chat-widget-close]");
  const cartToggleBtn = $("[data-cart-toggle]");
  const cartDrawer = $("[data-cart-drawer]");
  const cartCloseBtn = $("[data-cart-close]");
  const cartBackdrop = $("[data-cart-backdrop]");
  const cartBadge = $("[data-cart-badge]");

  const adminPortal = $("[data-admin-panel-portal]");
  const adminOpenPortalBtn = $("[data-open-dashboard]");
  const adminClosePortalBtn = $("[data-admin-close-portal]");
  const adminStatsRefreshBtn = $("[data-admin-stats-refresh]");
  const adminLogoutBtns = $$("[data-admin-logout], [data-admin-logout-btn]");

  // Mobile Nav
  const hamburgerBtn = $("[data-hamburger]");
  const mobileNav = $("[data-mobile-nav]");
  const mobileNavBackdrop = $("[data-mobile-nav-backdrop]");
  const mobileNavCloseBtn = $("[data-mobile-nav-close]");

  // ── Utilities ──────────────────────────────────────────

  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function postJson(url, payload, options = {}) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Request failed.");
    return data;
  }

  function setStatus(element, text, kind) {
    if (!element) return;
    element.textContent = text;
    element.classList.remove("is-success", "is-error");
    if (kind) element.classList.add(kind);
  }

  function starsHtml(rating, max = 5) {
    return Array.from({ length: max }, (_, i) => (i < rating ? "★" : "☆")).join("");
  }

  function formatPrice(item, currency) {
    if (item.price_display) return item.price_display;
    if (item.price == null) return "";
    return `${currency}${Number(item.price).toFixed(Number.isInteger(item.price) ? 0 : 2)}`;
  }

  function normalizePhone(phone) {
    if (!phone) return "";
    const hasPlus = phone.trim().startsWith("+");
    const digits = phone.replace(/\D/g, "");
    return hasPlus ? `+${digits}` : digits;
  }

  function isValidPhone(phone) {
    const digits = phone.replace(/\D/g, "");
    return digits.length >= 9 && digits.length <= 15;
  }

  // ── Dark Mode ──────────────────────────────────────────

  function initTheme() {
    const saved = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = saved || (prefersDark ? "dark" : "light");
    applyTheme(theme);
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
    if (themeToggle) {
      themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
      themeToggle.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "dark" ? "light" : "dark");
  }

  // ── Overlay Controls ──────────────────────────────────

  function toggleChat(force) {
    if (!chatWidget) return;
    const isOpen = typeof force === 'boolean' ? force : !chatWidget.classList.contains("is-open");
    chatWidget.classList.toggle("is-open", isOpen);
    if (isOpen && chatInput) setTimeout(() => chatInput.focus(), 300);
  }

  function toggleCart(force) {
    if (!cartDrawer || !cartBackdrop) return;
    const isOpen = typeof force === 'boolean' ? force : !cartDrawer.classList.contains("is-open");
    cartDrawer.classList.toggle("is-open", isOpen);
    if (cartBackdrop) cartBackdrop.classList.toggle("is-open", isOpen);
  }

  function toggleAdminPortal(force) {
    if (!adminPortal) return;
    const isOpen = typeof force === 'boolean' ? force : !adminPortal.classList.contains("is-open");
    adminPortal.classList.toggle("is-open", isOpen);
    adminPortal.style.display = isOpen ? "block" : "none";
    if (isOpen) {
      loadAdminStats();
      loadAdminReservations();
      loadAdminOrders();
    }
  }

  function toggleMobileNav(force) {
    if (!mobileNav || !mobileNavBackdrop) return;
    const isOpen = typeof force === 'boolean' ? force : !mobileNav.classList.contains("is-open");
    mobileNav.classList.toggle("is-open", isOpen);
    mobileNavBackdrop.classList.toggle("is-open", isOpen);
    document.body.style.overflow = isOpen ? "hidden" : "";
  }

  function initRevealAnimations() {
    if (!revealObserver) {
      revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          // Toggle visibility for main layout sections
          entry.target.classList.toggle("is-visible", entry.isIntersecting);
        });
      }, { threshold: 0.05, rootMargin: "0px 0px -50px 0px" });
    }

    $$(".page-section, .hero, .panel, .menu-section").forEach(el => {
      if (!el.classList.contains("reveal")) {
        el.classList.add("reveal");
        revealObserver.observe(el);
      }
    });
  }

  function updateCartBadge() {
    if (!cartBadge) return;
    const count = orderCart.reduce((sum, item) => sum + item.quantity, 0);
    cartBadge.textContent = count;
    cartBadge.style.display = count > 0 ? "flex" : "none";
  }

  // ── Chat ───────────────────────────────────────────────

  function appendMessage(role, content) {
    if (!chatLog) return;
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.innerHTML = escapeHtml(content);
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function clearConversation() {
    if (chatLog) chatLog.replaceChildren();
  }

  function seedConversation() {
    appendMessage(
      "assistant",
      `Hi, I'm the host at ${profile.name || "the restaurant"}. Ask me about the menu, reservations, or what tastes right tonight.`
    );
  }

  async function handleChatSubmit(event) {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    appendMessage("user", message);
    chatInput.value = "";
    chatInput.disabled = true;
    const controller = new AbortController();
    activeChatRequest = controller;

    try {
      const data = await postJson("/api/chat", { message }, { signal: controller.signal });
      appendMessage("assistant", data.reply || "I'm sorry, I couldn't answer that right now.");
    } catch (error) {
      if (error.name !== "AbortError") appendMessage("meta", error.message);
    } finally {
      if (activeChatRequest === controller) {
        activeChatRequest = null;
        chatInput.disabled = false;
        chatInput.focus();
      }
    }
  }

  async function handleResetChat() {
    if (resetChatButton) resetChatButton.disabled = true;
    if (activeChatRequest) {
      activeChatRequest.abort();
      activeChatRequest = null;
    }
    try {
      await postJson("/api/chat/reset", {});
      clearConversation();
      seedConversation();
      if (chatInput) chatInput.value = "";
    } catch (error) {
      if (error.name !== "AbortError") appendMessage("meta", error.message);
    } finally {
      if (chatInput) {
        chatInput.disabled = false;
        chatInput.focus();
      }
      if (resetChatButton) resetChatButton.disabled = false;
    }
  }

  // ── Menu ───────────────────────────────────────────────

  function renderMenu(menu) {
    if (!menuGrid || !menu || !Array.isArray(menu.sections)) return;
    const currency = menu.currency || "$";

    menuGrid.innerHTML = menu.sections
      .map((section, sIdx) => {
        const items = Array.isArray(section.items) ? section.items : [];
        return `
          <article class="menu-section" id="${escapeHtml(section.name)}">
            <div class="menu-section__header">
              <h3>${escapeHtml(section.name)}</h3>
              <span>${items.length} item${items.length !== 1 ? "s" : ""}</span>
            </div>
            <ul class="menu-list">
              ${items
                .map((item, iIdx) => {
                  const tags = Array.isArray(item.tags) ? item.tags : [];
                  const price = formatPrice(item, currency);
                  const delay = (sIdx * 2 + iIdx) * 50;

                  const adminStockHtml = isAdmin ? `
                    <div class="admin-stock-control" style="display:flex;align-items:center;gap:8px;margin-top:6px;padding:6px 10px;border-radius:6px;background:var(--surface-raised);border:1px dashed var(--surface-border);">
                      <span style="font-size:0.75rem;color:var(--text-tertiary);">Admin Control:</span>
                      <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:0.8rem;">
                        <input type="checkbox" ${!item.out_of_stock ? 'checked' : ''}
                          data-stock-toggle="${escapeHtml(item.name)}" />
                        In Stock
                      </label>
                    </div>` : '';

                  const imageHtml = item.image_url ? `
                    <div class="menu-item__image-wrap">
                      <img src="${item.image_url}" alt="${escapeHtml(item.name)}" class="menu-item__img" loading="lazy">
                    </div>` : '';

                  return `
                    <li class="menu-item reveal ${item.highlight ? "is-highlight" : ""}${item.out_of_stock ? " is-out-of-stock" : ""}"
                        style="transition-delay: ${delay}ms;">
                      ${imageHtml}
                      <div class="menu-item__content">
                        <div class="menu-item__top">
                          <strong>${escapeHtml(item.name)}</strong>
                          <span>${escapeHtml(price)}</span>
                        </div>
                        <p>${escapeHtml(item.description || "")}</p>
                        ${item.out_of_stock
                          ? '<div class="tag-row"><span style="background:var(--error);color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;">Out of Stock</span></div>'
                          : (tags.length ? `<div class="tag-row">${tags.map((t) => `<span>${escapeHtml(t)}</span>`).join("")}</div>` : "")}
                        
                        <div class="menu-item__bottom-actions" style="display:flex; gap:8px; margin-top:20px;">
                          ${document.body.dataset.isAdmin === "true" ? "" : `
                          <button class="menu-item__order-btn" type="button" style="flex-grow:1; border-radius:var(--r-full); padding:8px 16px;"
                            data-add-to-order='${escapeHtml(JSON.stringify({ name: item.name, price: item.price }))}'
                            ${item.out_of_stock ? 'disabled style="opacity:0.4;cursor:not-allowed;"' : ''}
                          >${item.out_of_stock ? 'Sold Out' : '+ Add'}</button>
                          `}
                          <button class="btn btn-ghost btn-sm" style="padding:4px 12px; font-size:0.75rem; border:1px solid var(--border); border-radius:var(--r-full);" data-toggle-details>Details</button>
                        </div>

                        <div class="menu-item__details" style="margin-top:12px; font-size:0.85rem; color:var(--text-secondary); border-top:1px solid var(--border); padding-top:12px; display:none;">
                           ${escapeHtml(item.detailed_description || "No further details available.")}
                        </div>
                        ${adminStockHtml}
                      </div>
                    </li>`;
                })
                .join("")}
            </ul>

          </article>`;
      })
      .join("");

    $$("[data-add-to-order]", menuGrid).forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const itemData = JSON.parse(btn.dataset.addToOrder);
        addToOrder(itemData.name, itemData.price);
      });
    });

    $$("[data-toggle-details]", menuGrid).forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const item = btn.closest(".menu-item");
        const details = item.querySelector(".menu-item__details");
        const isVisible = details.style.display === "block";
        details.style.display = isVisible ? "none" : "block";
        item.classList.toggle("is-expanded", !isVisible);
        btn.textContent = isVisible ? "Details" : "Close";
      });
    });



    if (isAdmin) {
      $$("[data-stock-toggle]", menuGrid).forEach((chk) => {
        chk.addEventListener("change", async () => {
          const name = chk.dataset.stockToggle;
          const outOfStock = !chk.checked;
          try {
            await postJson(`/api/menu/stock`, {item_name: name, out_of_stock: outOfStock}, {method: "PUT"});
            await refreshMenu();
          } catch(e) {
            alert("Failed: " + e.message);
            await refreshMenu();
          }
        });
      });
    }
  }

  async function refreshMenu() {
    if (!menuGrid) return;
    try {
      const response = await fetch("/api/menu", { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("Menu refresh failed.");
      menuState = await response.json();
      renderMenu(menuState);
    } catch (error) {
      console.error(error);
    }
  }

  async function searchMenu(query) {
    if (!query.trim()) {
      renderMenu(menuState);
      return;
    }
    try {
      const response = await fetch(`/api/menu/search?q=${encodeURIComponent(query)}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("Search failed.");
      const data = await response.json();

      if (data.results.length === 0) {
        menuGrid.innerHTML = `<div class="order-empty"><p>No items match "${escapeHtml(query)}"</p></div>`;
      } else {
        const grouped = {};
        data.results.forEach((item) => {
          const sec = item.section || "Results";
          if (!grouped[sec]) grouped[sec] = [];
          grouped[sec].push(item);
        });
        const sections = Object.entries(grouped).map(([name, items]) => ({ name, items }));
        renderMenu({ ...menuState, sections });
      }
    } catch (error) {
      console.error(error);
    }
  }

  function handleMenuSearch() {
    if (!menuSearchInput) return;
    let debounce = null;
    menuSearchInput.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => searchMenu(menuSearchInput.value), 300);
    });
    const clearBtn = $("[data-clear-search]");
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        menuSearchInput.value = "";
        searchMenu("");
      });
    }
  }

  function filterMenuByCategory(category) {
    if (!menuGrid) return;
    const cleanCategory = (category || "").trim().toLowerCase();
    const sections = $$(".menu-section", menuGrid);
    
    sections.forEach((sec) => {
      const secHeader = sec.querySelector("h3");
      const secName = secHeader ? secHeader.textContent.trim().toLowerCase() : "";
      
      if (cleanCategory === "all" || secName === cleanCategory) {
        sec.style.display = "block";
        sec.classList.add("is-visible");
      } else {
        sec.style.display = "none";
        sec.classList.remove("is-visible");
      }
    });

    // Update active tab UI
    $$(".category-tab").forEach((tab) => {
      const tabCat = (tab.dataset.category || "").trim().toLowerCase();
      tab.classList.toggle("is-active", tabCat === cleanCategory);
    });

    // Update URL hash without scrolling
    if (cleanCategory !== "all") {
      history.replaceState(null, null, "#" + encodeURIComponent(category));
    } else {
      history.replaceState(null, null, window.location.pathname);
    }
  }

  function handleCategoryLinkClick(event) {
    const link = event.target.closest("a");
    if (!link || !link.hash) return;
    const category = decodeURIComponent(link.hash.substring(1));
    if (!category) return;

    // Check if we are on the menu page
    if (window.location.pathname.startsWith("/menu")) {
      event.preventDefault();
      filterMenuByCategory(category);
    }
  }

  function initCategoryFilters() {
    const filterContainer = $("[data-category-filters]");
    if (!filterContainer) return;

    filterContainer.addEventListener("click", (e) => {
      const tab = e.target.closest(".category-tab");
      if (tab) {
        filterMenuByCategory(tab.dataset.category);
      }
    });

    // Listen for category link clicks in the whole document (especially Nav)
    document.addEventListener("click", handleCategoryLinkClick);

    // Initial check from URL hash
    const hash = window.location.hash.substring(1);
    if (hash) {
      const decoded = decodeURIComponent(hash);
      setTimeout(() => filterMenuByCategory(decoded), 100);
    }
  }

  function handleTagFilters() {
    $$("[data-tag-filter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const isActive = btn.classList.contains("is-active");
        $$("[data-tag-filter]").forEach((b) => b.classList.remove("is-active"));
        if (!isActive) {
          btn.classList.add("is-active");
          searchMenu(btn.dataset.tagFilter);
        } else {
          renderMenu(menuState);
        }
        if (menuSearchInput) menuSearchInput.value = "";
      });
    });
  }

  // ── Reservation ────────────────────────────────────────

  async function updateAvailability() {
    if (!resDateInput || !resTimeInput) return;
    const date = resDateInput.value;
    const time = resTimeInput.value;
    if (!date || !time) return;
    checkAvailability(date, time);
  }

  function initPickers() {
    if (resDateInput) {
      flatpickr(resDateInput, {
        dateFormat: "Y-m-d",
        minDate: "today",
        defaultDate: "today",
        onChange: updateAvailability,
        onReady: (selectedDates, dateStr, instance) => {
          instance.calendarContainer.classList.add("glass-picker");
        }
      });
    }
    if (resTimeInput) {
      flatpickr(resTimeInput, {
        enableTime: true,
        noCalendar: true,
        dateFormat: "H:i",
        time_24hr: false,
        defaultDate: "19:00",
        onChange: updateAvailability,
        onReady: (selectedDates, dateStr, instance) => {
          instance.calendarContainer.classList.add("glass-picker");
        }
      });
    }
    // Automatically trigger initial availability check
    updateAvailability();
  }

  async function checkAvailability(date, time) {
    if (!resAvailBar) return;
    if (!date || !time) {
      resAvailBar.style.display = "none";
      return;
    }

    try {
      const response = await fetch(`/api/reservations/availability?date=${encodeURIComponent(date)}&time=${encodeURIComponent(time)}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return;
      const data = await response.json();
      resAvailBar.style.display = "block";
      const fillPercent = Math.min(100, Math.round((data.booked_seats / data.max_seats) * 100));
      resAvailFill.style.width = `${fillPercent}%`;
      resAvailBar.classList.toggle("is-full", data.is_full);
      resAvailText.textContent = data.is_full ? "Fully booked" : `${data.available_seats} seats available`;
    } catch (e) {}
  }

  async function lookupReservation() {
    const code = resLookupInput ? resLookupInput.value.trim() : "";
    if (!code || !resResultEl) return;

    try {
      const response = await fetch(`/api/reservations/${encodeURIComponent(code)}`, {
        headers: { Accept: "application/json" },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Not found.");

      const res = data.reservation;
      resResultEl.innerHTML = `
        <div class="reservation-detail">
          <div class="reservation-detail__row">
            <span class="reservation-detail__label">Status</span>
            <span class="reservation-status-badge is-${res.status}">${escapeHtml(res.status)}</span>
          </div>
          <div class="reservation-detail__row">
            <span class="reservation-detail__label">Guest</span>
            <span class="reservation-detail__value">${escapeHtml(res.guest_name)} (${res.party_size} guests)</span>
          </div>
          <div class="reservation-detail__row">
            <span class="reservation-detail__label">Date & Time</span>
            <span class="reservation-detail__value">${escapeHtml(res.reservation_date)} at ${escapeHtml(res.reservation_time)}</span>
          </div>
          ${res.status !== 'cancelled' ? `
          <div class="reservation-detail__row" style="margin-top: 12px; justify-content: flex-end; border: none;">
            <button class="btn btn-ghost btn-sm" style="color:var(--error);border-color:var(--error-border)" data-cancel-res="${escapeHtml(res.confirmation_code)}">Cancel reservation</button>
          </div>` : ''}
        </div>`;
        
      const cancelBtn = $("[data-cancel-res]", resResultEl);
      if (cancelBtn) cancelBtn.addEventListener("click", () => cancelReservation(code));
    } catch (error) {
      resResultEl.innerHTML = `<div class="status-card is-error">${escapeHtml(error.message)}</div>`;
    }
  }

  async function cancelReservation(code) {
    if (!confirm("Confirm cancellation?")) return;
    try {
      const response = await fetch(`/api/reservations/${encodeURIComponent(code)}/cancel`, {
        method: "POST",
        headers: { Accept: "application/json" },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to cancel.");
      lookupReservation();
      appendMessage("assistant", data.message);
    } catch (error) { alert(error.message); }
  }

  async function handleReservationSubmit(event) {
    event.preventDefault();
    const formData = new FormData(reservationForm);
    const payload = Object.fromEntries(formData.entries());

    if (payload.phone && !isValidPhone(payload.phone)) {
      setStatus(reservationStatus, "Invalid phone number.", "is-error");
      return;
    }
    payload.phone = normalizePhone(payload.phone);

    try {
      payload.party_size = Number(payload.party_size);
      const data = await postJson("/api/reservations", payload);
      setStatus(reservationStatus, data.message || "Reservation saved.", "is-success");
      appendMessage("assistant", data.message || "Your reservation is confirmed.");
      reservationForm.reset();
      checkAvailability();
    } catch (error) { setStatus(reservationStatus, error.message, "is-error"); }
  }

  // ── Feedback ───────────────────────────────────────────

  function initStarInput() {
    $$("[data-star]").forEach((btn) => {
      btn.addEventListener("click", () => {
        feedbackRating = Number(btn.dataset.star);
        updateStars();
      });
    });
  }

  function updateStars() {
    $$("[data-star]").forEach((b) => {
      const filled = Number(b.dataset.star) <= feedbackRating;
      b.textContent = filled ? "★" : "☆";
      b.classList.toggle("is-filled", filled);
    });
  }

  async function handleFeedbackSubmit(event) {
    event.preventDefault();
    const formData = new FormData(feedbackForm);
    if (feedbackRating < 1) {
      setStatus(feedbackStatus, "Please select a rating.", "is-error");
      return;
    }
    try {
      const data = await postJson("/api/feedback", {
        guest_name: formData.get("guest_name"),
        rating: feedbackRating,
        comment: formData.get("comment"),
      });
      setStatus(feedbackStatus, data.message || "Thank you!", "is-success");
      feedbackForm.reset();
      feedbackRating = 0;
      updateStars();
      loadFeedback();
    } catch (error) { setStatus(feedbackStatus, error.message, "is-error"); }
  }

  async function loadFeedback() {
    try {
      const response = await fetch("/api/feedback/recent", { headers: { Accept: "application/json" } });
      if (!response.ok) return;
      const data = await response.json();
      if (feedbackStatsEl) {
        feedbackStatsEl.innerHTML = `
          <div class="stat-card">
            <div class="stat-card__value">${data.average_rating?.toFixed(1) || "—"}</div>
            <div class="stat-card__label">Avg Rating</div>
          </div>
          <div class="stat-card">
            <div class="stat-card__value">${data.total || 0}</div>
            <div class="stat-card__label">Reviews</div>
          </div>`;
      }
      if (feedbackReviews) {
        feedbackReviews.innerHTML = (data.reviews || []).map(r => `
          <div class="review-card">
            <div class="review-card__header">
              <span class="review-card__name">${escapeHtml(r.guest_name)}</span>
              <span class="review-card__stars">${starsHtml(r.rating)}</span>
            </div>
            <p class="review-card__comment">${escapeHtml(r.comment)}</p>
          </div>`).join("");
      }
    } catch (error) {}
  }

  // ── Orders ─────────────────────────────────────────────

  function saveOrderCart() {
    localStorage.setItem("orderCart", JSON.stringify(orderCart));
  }

  function addToOrder(name, price) {
    const existing = orderCart.find((item) => item.name === name);
    if (existing) existing.quantity += 1;
    else orderCart.push({ name, unit_price: price || 0, quantity: 1 });
    saveOrderCart();
    renderOrderCart();
    updateCartBadge();
    toggleCart(true);
    appendMessage("meta", `Added ${name} to cart.`);
  }

  function removeFromOrder(index) {
    orderCart.splice(index, 1);
    saveOrderCart();
    renderOrderCart();
    updateCartBadge();
  }

  function renderOrderCart() {
    const listContainers = [orderItemsList, orderItemsDrawer].filter(Boolean);
    const totalContainers = [orderTotalEl, orderTotalDrawer].filter(Boolean);
    
    if (orderCart.length === 0) {
      listContainers.forEach(c => {
        c.innerHTML = `
          <div class="order-empty" style="text-align:center; padding:40px 20px;">
            <div style="font-size:3rem; margin-bottom:12px;">🛒</div>
            <p style="color:var(--text-tertiary)">Your cart is empty.</p>
          </div>`;
      });
      totalContainers.forEach(c => {
        c.innerHTML = `
          <div class="order-total">
            <span>Total</span>
            <strong>$0.00</strong>
          </div>`;
      });
      return;
    }

    const itemsHtml = orderCart.map((item, i) => `
      <div class="order-line-item reveal is-visible">
        <div class="order-line-item__content">
          <span class="order-line-item__name">${escapeHtml(item.name)}</span>
          <span class="order-line-item__quantity">${item.quantity} × $${item.unit_price.toFixed(2)}</span>
        </div>
        <div class="order-line-item__price">$${(item.unit_price * item.quantity).toFixed(2)}</div>
        <button class="order-line-item__remove" onclick="removeFromOrder(${i})" aria-label="Remove item">×</button>
      </div>`).join("");

    listContainers.forEach(c => c.innerHTML = itemsHtml);

    const subtotal = orderCart.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);
    const totalHtml = `
      <div class="order-total">
        <span>Total</span>
        <strong>$${subtotal.toFixed(2)}</strong>
      </div>`;
    
    totalContainers.forEach(c => c.innerHTML = totalHtml);
  }
  window.removeFromOrder = removeFromOrder; // Globally available for onclick

  async function handleOrderSubmit(event) {
    event.preventDefault();
    if (orderCart.length === 0) return setStatus(orderStatus, "Add items first.", "is-error");
    const formData = new FormData(orderForm);
    const payload = {
      guest_name: formData.get("order_guest_name"),
      phone: normalizePhone(formData.get("order_phone")),
      email: formData.get("email"),
      order_type: formData.get("order_type"),
      items: orderCart.map(i => ({ name: i.name, quantity: i.quantity, unit_price: i.unit_price }))
    };
    try {
      const data = await postJson("/api/orders", payload);
      setStatus(orderStatus, data.message || "Placed!", "is-success");
      orderCart = [];
      saveOrderCart();
      renderOrderCart();
      updateCartBadge();
      orderForm.reset();
    } catch (error) { setStatus(orderStatus, error.message, "is-error"); }
  }

  async function lookupOrder() {
    const orderId = orderLookupInput?.value.trim();
    if (!orderId || !orderResultEl) return;
    try {
      const response = await fetch(`/api/orders/${encodeURIComponent(orderId)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Not found.");
      const o = data.order;
      orderResultEl.innerHTML = `
        <div class="order-result">
          <div style="display:flex;justify-content:space-between">
            <strong>Order #${escapeHtml(o.order_id.substring(0,8))}</strong>
            <span class="status-badge is-${o.status}">${escapeHtml(o.status)}</span>
          </div>
          <p>$${o.total.toFixed(2)} · ${o.items.length} items</p>
        </div>`;
    } catch (error) { orderResultEl.innerHTML = `<p style="color:var(--error)">${escapeHtml(error.message)}</p>`; }
  }

  // ── Admin Section ──────────────────────────────────────

  async function checkAdmin() {
    try {
      // Add cache-buster to ensure we don't get a stale session state
      const response = await fetch("/admin/check?t=" + Date.now());
      const data = await response.json();
      if (data.is_admin) activateAdminMode();
    } catch (_) {}
  }

  let adminRefreshInterval = null;
  let charts = {};

  function toggleAdminPortal(show) {
    if (!adminPortal || isTogglingPortal) return;
    
    // Cooldown to prevent double-click vanishing race condition
    if (show) {
      isTogglingPortal = true;
      setTimeout(() => { isTogglingPortal = false; }, 400);
    }

    document.body.classList.toggle("admin-sidebar-open", false);
    adminPortal.style.display = show ? "flex" : "none";
    if (show) {
      loadAdminStats();
      loadAdminReservations();
      loadAdminOrders();
      loadAdminMenu();
      loadAdminFeedback();
    }
  }

  function activateAdminMode() {
    isAdmin = true;
    document.body.classList.add("is-admin");
    if (adminToggle) adminToggle.style.display = "none";
    if (adminOpenPortalBtn) adminOpenPortalBtn.style.display = "block";
    adminLogoutBtns.forEach(btn => btn.style.display = "block");
    $$("[data-nav-dashboard]").forEach(btn => btn.style.display = "inline-block");

    if (menuState) renderMenu(menuState);
    
    // Only fetch dashboard data if we're actually looking at the dashboard
    if ($("[data-stat-revenue]")) {
      loadAdminStats();
      loadAdminReservations();
      loadAdminOrders();
      loadAdminMenu();
      loadAdminFeedback();
    }

    if (adminRefreshInterval) clearInterval(adminRefreshInterval);
    adminRefreshInterval = setInterval(() => { 
      if ($("[data-stat-revenue]")) {
        loadAdminStats(); 
        loadAdminReservations(); 
        loadAdminOrders(); 
        loadAdminFeedback();
      }
    }, 60000);
  }

  function deactivateAdminMode() {
    isAdmin = false;
    document.body.classList.remove("is-admin", "admin-sidebar-open");
    if (adminToggle) {
      adminToggle.classList.remove("is-active");
      adminToggle.style.display = "inline-flex";
    }
    if (adminOpenPortalBtn) adminOpenPortalBtn.style.display = "none";
    adminLogoutBtns.forEach(btn => btn.style.display = "none");
    $$("[data-nav-dashboard]").forEach(btn => btn.style.display = "none");
    if (adminRefreshInterval) clearInterval(adminRefreshInterval);
    if (menuState) renderMenu(menuState);
  }

  async function loadAdminStats() {
    try {
      const res = await fetch("/api/admin/stats");
      const data = await res.json();
      
      // Handle Quota/Stale Warning
      const quotaWarning = $("[data-admin-quota-warning]");
      if (data.stale) {
        if (quotaWarning) {
          quotaWarning.innerHTML = `⚠️ Data from cache - Firestore quota limit reached.`;
          quotaWarning.style.display = "block";
        }
      } else if (quotaWarning) {
        quotaWarning.style.display = "none";
      }

      $("[data-stat-revenue]").textContent = `$ ${data.total_revenue.toLocaleString()}`;
      $("[data-stat-orders]").textContent = data.order_count;
      $("[data-stat-reservations]").textContent = data.res_count;
      $("[data-stat-satisfaction]").textContent = "94%";
      renderCharts(data);
    } catch (e) {}
  }

  function renderCharts(data) {
    const ctxRev = document.getElementById('revenueChart')?.getContext('2d');
    const ctxOps = document.getElementById('opsChart')?.getContext('2d');
    const ctxItems = document.getElementById('itemsChart')?.getContext('2d');
    if (!ctxRev || !ctxItems || !ctxOps) return;

    // Chart 1: Revenue (Line)
    if (charts.rev) charts.rev.destroy();
    charts.rev = new Chart(ctxRev, {
      type: 'line',
      data: {
        labels: (data.daily_revenue || []).map(d => d.date),
        datasets: [{ label: 'Revenue ($)', data: (data.daily_revenue || []).map(d => d.total), borderColor: '#b87333', backgroundColor: 'rgba(184,115,51,0.1)', fill: true, tension: 0.4 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });

    // Chart 2: Operations Balance (Bar)
    if (charts.ops) charts.ops.destroy();
    charts.ops = new Chart(ctxOps, {
      type: 'bar',
      data: {
        labels: ['Bookings', 'Orders'],
        datasets: [{
          data: [data.res_count || 0, data.order_count || 0],
          backgroundColor: ['#b87333', '#3ab47a'],
          borderRadius: 8
        }]
      },
      options: { 
        responsive: true, 
        maintainAspectRatio: false, 
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } } }
      }
    });

    // Chart 3: Popular Items (Doughnut)
    if (charts.items) charts.items.destroy();
    charts.items = new Chart(ctxItems, {
      type: 'doughnut',
      data: {
        labels: (data.popular_items || []).map(i => i.name),
        datasets: [{ data: (data.popular_items || []).map(i => i.count), backgroundColor: ['#b87333', '#d18d4d', '#7a736d', '#3ab47a', '#e65545'], borderWidth: 0 }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: 'rgba(255,255,255,0.7)',
              font: { size: 11 },
              padding: 15,
              usePointStyle: true
            }
          }
        },
        cutout: '70%'
      }
    });
  }

  function getNextOrderStatus(current) {
    const map = {
      'awaiting_approval': 'received',
      'received': 'preparing',
      'preparing': 'ready',
      'ready': 'completed'
    };
    return map[current] || null;
  }

  function getStatusActionLabel(status) {
    const map = {
      'awaiting_approval': 'Accept Order',
      'received': 'Start Preparing',
      'preparing': 'Mark Ready',
      'ready': 'Complete Order'
    };
    return map[status] || 'Update';
  }

  async function loadAdminReservations() {
    const rBody = $("[data-admin-res-body]");
    if (!rBody) return;
    try {
      const res = await fetch("/api/reservations/recent");
      const data = await res.json();
      rBody.innerHTML = (data.reservations || []).map(r => `
        <tr>
          <td><code style="font-size:0.75rem; color:var(--accent);">${r.confirmation_code}</code></td>
          <td><strong>${escapeHtml(r.guest_name)}</strong></td>
          <td>${escapeHtml(r.reservation_date)} @ ${escapeHtml(r.reservation_time)}</td>
          <td>${r.party_size} px</td>
          <td style="font-size:0.8rem; color:var(--text-tertiary); max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(r.notes || '')}">
            ${escapeHtml(r.notes || '-')}
          </td>
          <td style="text-align:right">
            ${r.status === 'pending_review' ? `
              <div style="display:flex; gap:8px; justify-content:flex-end;">
                <button class="btn btn-primary btn-sm" data-admin-action="approve-res" data-id="${r.confirmation_code}">Approve</button>
                <button class="btn btn-ghost btn-sm" style="color:var(--error)" data-admin-action="cancel-res" data-id="${r.confirmation_code}">Cancel</button>
              </div>
            ` : (r.status === 'confirmed' ? `
              <div style="display:flex; gap:8px; justify-content:flex-end; align-items:center;">
                <span class="mc-badge" style="background:rgba(58,180,122,0.1); color:#3ab47a">Confirmed</span>
                <button class="btn btn-ghost btn-xs" style="color:var(--error); font-size:0.7rem; padding:2px 8px;" data-admin-action="cancel-res" data-id="${r.confirmation_code}">Cancel</button>
              </div>
            ` : `<span style="font-size:0.8rem; color:var(--text-tertiary); text-transform:capitalize;">${r.status}</span>`)}
          </td>
        </tr>`).join("");

      // Update Dashboard Home Summary
      const homeRes = $("[data-dashboard-res-pending]");
      if (homeRes) {
        const pending = (data.reservations || []).filter(r => r.status === 'pending_review');
        if (pending.length) {
          homeRes.innerHTML = pending.map(r => `
            <tr>
              <td><strong>${escapeHtml(r.guest_name)}</strong></td>
              <td style="font-size:0.75rem; color:var(--text-tertiary)">${r.reservation_time}</td>
              <td style="text-align:right">
                 <button class="btn btn-primary btn-sm" data-admin-action="approve-res" data-id="${r.confirmation_code}">Approve</button>
                 <button class="btn btn-ghost btn-sm" style="color:var(--error)" data-admin-action="cancel-res" data-id="${r.confirmation_code}">Cancel</button>
              </td>
            </tr>
          `).join("");
        } else {
          homeRes.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:12px; color:var(--text-tertiary)">Clear</td></tr>`;
        }
      }
      
      if (!data.reservations?.length) {
        rBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-tertiary); padding:20px;">No requests found</td></tr>`;
      }
    } catch (e) {}
  }

  window.updateAdminResStatus = async (code, status) => {
    await postJson(`/api/reservations/${code}/status`, { status }, { method: "PUT" });
    loadAdminReservations(); loadAdminStats();
  };

  window.updateAdminOrderStatus = async (orderId, status) => {
    await postJson(`/api/orders/${orderId}/status`, { status }, { method: "PUT" });
    loadAdminOrders(); loadAdminStats();
  };

  async function loadAdminOrders() {
    const oBody = $("[data-admin-orders-body]");
    if (!oBody) return;
    try {
      const res = await fetch("/api/orders/recent");
      const data = await res.json();
      oBody.innerHTML = (data.orders || []).map(o => `
        <tr>
          <td><code style="font-size:0.75rem;">#${(o.order_id || '').slice(0,6)}</code></td>
          <td><strong>${escapeHtml(o.guest_name)}</strong></td>
          <td>${escapeHtml(o.order_type)}</td>
          <td>$ ${(o.total || 0).toFixed(2)}</td>
          <td style="text-align:right">
            ${['completed', 'cancelled'].includes(o.status) ? 
              `<span style="color:var(--text-tertiary); text-transform:capitalize;">${o.status.replace("_", " ")}</span>` : 
              `
              <div style="display:flex; gap:8px; justify-content:flex-end; align-items:center;">
                <button class="btn btn-primary btn-sm" 
                  data-admin-action="progress-order" 
                  data-id="${o.order_id}"
                  data-next="${getNextOrderStatus(o.status)}">
                  ${getStatusActionLabel(o.status)}
                </button>
                <button class="btn btn-ghost btn-xs" style="color:var(--error)" data-admin-action="cancel-order" data-id="${o.order_id}">Cancel</button>
              </div>
            `}
          </td>
        </tr>`).join("");

      // Update Dashboard Home Summary
      const homeOrders = $("[data-dashboard-orders-pending]");
      if (homeOrders) {
        const pending = (data.orders || []).filter(o => !['completed', 'cancelled'].includes(o.status));
        if (pending.length) {
          homeOrders.innerHTML = pending.map(o => `
            <tr>
              <td><code style="font-size:0.75rem;">#${o.order_id.slice(0,4)}</code></td>
              <td style="font-size:0.75rem; color:var(--text-tertiary); text-transform:capitalize;">${o.status.replace("_", " ")}</td>
              <td style="text-align:right">
                 <div style="display:flex; gap:4px; justify-content:flex-end; align-items:center;">
                   <button class="btn btn-primary btn-xs" data-admin-action="progress-order" data-id="${o.order_id}" data-next="${getNextOrderStatus(o.status)}">
                      ${o.status === 'awaiting_approval' ? 'Accept' : (o.status === 'ready' ? 'Complete' : 'Next')}
                   </button>
                   <button class="btn btn-ghost btn-xs" style="color:var(--error); font-size:0.65rem;" data-admin-action="cancel-order" data-id="${o.order_id}">Cancel</button>
                 </div>
              </td>
            </tr>
          `).join("");
        } else {
          homeOrders.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:12px; color:var(--text-tertiary)">Clear</td></tr>`;
        }
      }

      if (!data.orders?.length) {
        oBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-tertiary); padding:20px;">Queue empty</td></tr>`;
      }
    } catch (e) {}
  }

  async function loadAdminFeedback() {
    const fBody = $("[data-admin-reviews-body]");
    if (!fBody) return;
    try {
      const res = await fetch("/api/feedback/recent?limit=50");
      const data = await res.json();
      fBody.innerHTML = (data.reviews || []).map(r => {
        let dateStr = r.created_at || '';
        if (dateStr.includes('T')) {
          const parts = dateStr.split('T');
          dateStr = parts[0] + ' ' + parts[1];
        }
        return `
        <tr>
          <td><strong>${escapeHtml(r.guest_name)}</strong></td>
          <td><span style="color:var(--accent); font-weight:bold;">${starsHtml(r.rating)}</span></td>
          <td style="font-size:0.9rem; color:var(--text-secondary); max-width:400px; word-break:break-word;">
            ${escapeHtml(r.comment)}
          </td>
          <td style="font-size:0.8rem; color:var(--text-tertiary);">${escapeHtml(dateStr)}</td>
        </tr>`;
      }).join("");

      if (!data.reviews?.length) {
        fBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-tertiary); padding:20px;">No reviews yet</td></tr>`;
      }
    } catch (e) {
      console.error("Failed to load admin reviews:", e);
    }
  }

  function loadAdminMenu() {
    const mBody = $("[data-admin-menu-body]");
    if (!mBody || !menuState) return;
    
    let rows = [];
    menuState.sections.forEach(section => {
      section.items.forEach(item => {
        rows.push(`
          <tr>
            <td><strong>${escapeHtml(item.name)}</strong></td>
            <td>$ ${item.price}</td>
            <td><span style="font-size:0.7rem; color:var(--text-tertiary)">${item.tags.join(", ")}</span></td>
            <td style="text-align:right; display:flex; gap:8px; justify-content:flex-end;">
              <button class="stock-toggle ${item.out_of_stock ? 'is-out-of-stock' : 'is-in-stock'}" 
                data-admin-action="toggle-stock" 
                data-id="${escapeHtml(item.name)}" 
                data-status="${item.out_of_stock}">
                ${item.out_of_stock ? '🚫 Out of Stock' : '✅ In Stock'}
              </button>
              <button class="stock-toggle is-out-of-stock" 
                style="cursor:pointer;" 
                onclick="removeMenuItem('${escapeHtml(item.name).replace(/'/g, "\\'")}')">
                🗑 Remove
              </button>
            </td>
          </tr>`);
      });
    });
    mBody.innerHTML = rows.join("");
  }

  window.removeMenuItem = async (itemName) => {
    const confirmed = await adminConfirm("Remove Item", `Are you sure you want to remove "${itemName}" from the menu?`);
    if (!confirmed) return;

    try {
      const response = await fetch("/api/menu/items", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_name: itemName }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to remove item.");
      
      await refreshMenu();
      loadAdminMenu();
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  async function handleAddMenuItem(event) {
    event.preventDefault();
    const form = event.target;
    const fd = new FormData(form);
    const statusEl = $("[data-add-item-status]");

    try {
      const response = await fetch("/api/menu/items", {
        method: "POST",
        body: fd,  // Send as multipart/form-data (supports file upload)
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Request failed.");

      if (statusEl) {
        statusEl.style.display = "inline-block";
        statusEl.classList.remove("is-error");
        statusEl.classList.add("is-success");
        statusEl.textContent = data.message || "Item added!";
      }
      form.reset();
      await refreshMenu();
      loadAdminMenu();
      setTimeout(() => { if (statusEl) statusEl.style.display = "none"; }, 4000);
    } catch (e) {
      if (statusEl) {
        statusEl.style.display = "inline-block";
        statusEl.classList.remove("is-success");
        statusEl.classList.add("is-error");
        statusEl.textContent = e.message || "Failed to add item.";
      }
    }
  }
  
  /**
   * Custom Asynchronous Confirmation Modal for Admin Actions
   * Fixes Chrome race conditions with native confirm()
   */
  async function adminConfirm(title, message) {
    const modal = $("[data-admin-confirm-modal]");
    console.log("adminConfirm requested:", title, !!modal);
    if (!modal) return confirm(message);
    
    return new Promise((resolve) => {
      const titleEl = modal.querySelector("[data-confirm-title]");
      const msgEl = modal.querySelector("[data-confirm-message]");
      if (titleEl) titleEl.textContent = title;
      if (msgEl) msgEl.textContent = message;
      
      modal.setAttribute("style", "display: flex !important;"); 
      
      const handler = (e) => {
        const btn = e.target.closest("[data-confirm-btn]");
        if (!btn) return;
        
        const result = btn.dataset.confirmBtn === "true";
        console.log("adminConfirm result:", result);
        modal.style.display = "none";
        modal.removeEventListener("click", handler);
        resolve(result);
      };
      
      modal.addEventListener("click", handler);
    });
  }

  window.updateAdminResStatus = async (code, status) => {
    try {
      console.log("Updating Reservation:", code, status);
      const res = await postJson(`/api/reservations/${code}/status`, { status }, { method: "PUT" });
      console.log("Update Success:", res);
      loadAdminReservations(); loadAdminStats();
    } catch (err) {
      console.error("Update Failed:", err);
      alert("Reservation update failed: " + err.message);
    }
  };

  window.updateAdminOrderStatus = async (orderId, status) => {
    try {
      console.log("Updating Order:", orderId, status);
      const res = await postJson(`/api/orders/${orderId}/status`, { status }, { method: "PUT" });
      console.log("Update Success:", res);
      loadAdminOrders(); loadAdminStats();
    } catch (err) {
      console.error("Update Failed:", err);
      alert("Order update failed: " + err.message);
    }
  };

  function initAdminTabs() {
    const portal = $("[data-admin-panel-portal]");
    if (!portal) return;

    portal.addEventListener("click", (e) => {
      const tabBtn = e.target.closest("[data-admin-tab]");
      if (!tabBtn) return;

      const tabId = tabBtn.dataset.adminTab;

      // Update Buttons
      portal.querySelectorAll("[data-admin-tab]").forEach(btn => btn.classList.remove("is-active"));
      tabBtn.classList.add("is-active");

      // Update Panes
      portal.querySelectorAll("[data-admin-pane]").forEach(pane => pane.classList.remove("is-active"));
      const targetPane = portal.querySelector(`[data-admin-pane="${tabId}"]`);
      if (targetPane) targetPane.classList.add("is-active");
    });
  }

  function initDashboardSubTabs() {
    const subNav = $("[data-admin-panel-portal] .admin-sub-nav");
    if (!subNav) return;

    subNav.addEventListener("click", (e) => {
      const tabBtn = e.target.closest("[data-dashboard-tab]");
      if (!tabBtn) return;

      const tabId = tabBtn.dataset.dashboardTab;

      // Update Tabs
      subNav.querySelectorAll("[data-dashboard-tab]").forEach(btn => btn.classList.remove("is-active"));
      tabBtn.classList.add("is-active");

      // Update Panes
      const portal = $("[data-admin-panel-portal]");
      portal.querySelectorAll(".dashboard-sub-pane").forEach(pane => {
        pane.classList.remove("is-active");
        pane.style.display = "none";
      });

      const targetPane = portal.querySelector(`[data-dashboard-pane="${tabId}"]`);
      if (targetPane) {
        targetPane.classList.add("is-active");
        targetPane.style.display = "block";
      }
    });
  }

  function initAdminActions() {
    const portal = $("[data-admin-panel-portal]");
    if (!portal) return;

    portal.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-admin-action]");
      if (!btn) return;

      const action = btn.dataset.adminAction;
      const id = btn.dataset.id;

      try {
        if (action === "toggle-stock") {
          const isOut = btn.dataset.status === "true";
          await postJson(`/api/menu/stock`, { item_name: id, out_of_stock: !isOut }, { method: "PUT" });
          await refreshMenu();
          loadAdminMenu();
        } else {
          btn.disabled = true;
          if (action === "approve-res") {
            await window.updateAdminResStatus(id, "confirmed");
          } else if (action === "cancel-res") {
            if(await adminConfirm("Cancel Reservation", "Are you sure you want to cancel this booking?")) {
              await window.updateAdminResStatus(id, "cancelled");
            } else btn.disabled = false;
          } else if (action === "accept-order") {
            await window.updateAdminOrderStatus(id, "received");
          } else if (action === "progress-order") {
            const next = btn.dataset.next;
            if (next && next !== "null") await window.updateAdminOrderStatus(id, next);
          } else if (action === "cancel-order") {
            if(await adminConfirm("Cancel Order", "Are you sure you want to cancel this order? This cannot be undone.")) {
              await window.updateAdminOrderStatus(id, "cancelled");
            } else btn.disabled = false;
          }
          await loadAdminStats();
        }
      } catch (err) {
        alert("Action failed: " + err.message);
        btn.disabled = false;
      }
    });
  }

  async function handleAdminLogin(event) {
    event.preventDefault();
    const fd = new FormData(adminLoginForm);
    try {
      const data = await postJson("/admin/login", { username: fd.get("admin_username"), password: fd.get("admin_password") });
      if (data.is_admin) {
        if (adminModal) adminModal.classList.remove("is-open");
        // Restore direct redirect as it is more reliable for session persistence on the new page
        window.location.href = data.redirect || "/admin/dashboard";
      }
    } catch (e) { alert(e.message); }
  }

  async function handleAdminLogout(event) {
    if (event && event.preventDefault) event.preventDefault();
    try {
      deactivateAdminMode();
      // Clear Service Worker caches to force the browser to see the logged-out state
      if ('caches' in window) {
        const names = await caches.keys();
        await Promise.all(names.map(name => caches.delete(name)));
      }
      await fetch("/admin/logout", { method: "POST" });
      window.location.href = "/?logout=" + Date.now();
    } catch (e) {
      window.location.href = "/";
    }
  }

  // ── Wiring ─────────────────────────────────────────────

  async function init() {
    if (hasInitialized) return;
    hasInitialized = true;
    
    initTheme();
    if (themeToggle) themeToggle.addEventListener("click", toggleTheme);
    
    // Mobile nav
    if (hamburgerBtn) hamburgerBtn.addEventListener("click", () => toggleMobileNav(true));
    if (mobileNavCloseBtn) mobileNavCloseBtn.addEventListener("click", () => toggleMobileNav(false));
    if (mobileNavBackdrop) mobileNavBackdrop.addEventListener("click", () => toggleMobileNav(false));
    // Close mobile nav when a link is clicked
    if (mobileNav) {
      mobileNav.querySelectorAll("a").forEach(link => {
        link.addEventListener("click", () => toggleMobileNav(false));
      });
    }
    
    if (chatFab) chatFab.addEventListener("click", () => toggleChat());
    if (chatCloseBtn) chatCloseBtn.addEventListener("click", () => toggleChat(false));
    if (cartToggleBtn) cartToggleBtn.addEventListener("click", () => toggleCart());
    if (cartCloseBtn) cartCloseBtn.addEventListener("click", () => toggleCart(false));
    if (cartBackdrop) cartBackdrop.addEventListener("click", () => toggleCart(false));
    if (chatForm) chatForm.addEventListener("submit", handleChatSubmit);
    if (resetChatButton) resetChatButton.addEventListener("click", handleResetChat);
    if (reservationForm) reservationForm.addEventListener("submit", handleReservationSubmit);
    if (resDateInput) resDateInput.addEventListener("change", checkAvailability);
    if (resTimeInput) resTimeInput.addEventListener("change", checkAvailability);
    if (resLookupBtn) resLookupBtn.addEventListener("click", lookupReservation);
    if (feedbackForm) feedbackForm.addEventListener("submit", handleFeedbackSubmit);
    initStarInput(); loadFeedback();
    renderOrderCart(); if (orderForm) orderForm.addEventListener("submit", handleOrderSubmit);
    if (orderLookupBtn) orderLookupBtn.addEventListener("click", lookupOrder);
    if (adminToggle) adminToggle.addEventListener("click", async () => { 
      if(isAdmin){ 
        if(await adminConfirm("Sign Out", "Are you sure you want to exit Mission Control?")) handleAdminLogout(); 
      } else adminModal.classList.add("is-open"); 
    });
    if (adminCloseBtn) adminCloseBtn.addEventListener("click", () => adminModal.classList.remove("is-open"));
    if (adminLoginForm) adminLoginForm.addEventListener("submit", handleAdminLogin);
    if (adminOpenPortalBtn) adminOpenPortalBtn.addEventListener("click", () => toggleAdminPortal(true));
    if (adminClosePortalBtn) adminClosePortalBtn.addEventListener("click", () => toggleAdminPortal(false));
    if (adminStatsRefreshBtn) {
      adminStatsRefreshBtn.addEventListener("click", () => {
        loadAdminStats();
        loadAdminReservations();
        loadAdminOrders();
        loadAdminMenu();
        loadAdminFeedback();
      });
    }
    adminLogoutBtns.forEach(btn => btn.addEventListener("click", handleAdminLogout));
    
    // Cart Drawer Listeners
    if (cartCloseBtn) cartCloseBtn.addEventListener("click", () => toggleCart(false));
    $$("[data-cart-close]").forEach(btn => btn.addEventListener("click", () => toggleCart(false)));
    if (cartBackdrop) cartBackdrop.addEventListener("click", () => toggleCart(false));

    initAdminTabs();
    initDashboardSubTabs();
    initAdminActions();
    
    // Wire up the add-menu-item form
    const addItemForm = $("[data-admin-add-item-form]");
    if (addItemForm) addItemForm.addEventListener("submit", handleAddMenuItem);
    
    // If we're physically on the admin dashboard, we MUST be an admin
    if ($("[data-admin-panel-portal]")) isAdmin = true;

    // Sequential init to prevent double-render flickering
    if (isAdmin) {
      activateAdminMode();
    } else {
      await checkAdmin(); 
    }
    await refreshMenu(); 
    
    handleMenuSearch(); 
    handleTagFilters();
    initCategoryFilters();
    initPickers();
    initRevealAnimations();
    seedConversation();
    
    // Final sync of cart UI on load
    renderOrderCart();
    updateCartBadge();

    // Auto-open admin modal if ?admin=login is in the URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("admin") === "login" && adminModal) {
      adminModal.classList.add("is-open");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
