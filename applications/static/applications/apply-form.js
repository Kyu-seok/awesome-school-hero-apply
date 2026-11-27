// 신청 폼: POST /api/applications/를 호출하고 필드별 오류와 접수 완료 화면을 보여준다.
// 날짜 규칙의 최종 판정은 서버(applications/services.py)가 한다. 여기서는 고르는 동안 미리 안내만 한다.
(function () {
  const form = document.getElementById("apply-form");
  if (!form) return;
  const done = document.getElementById("apply-done");
  const submitButton = form.querySelector('button[type="submit"]');
  const submitLabel = submitButton.querySelector(".button__label");
  const preferredInput = form.elements.preferred_class_date;
  const contactInput = form.elements.contact_date;
  const NUMBER_FIELDS = ["class_count", "session_count"];
  let submitting = false;

  function payload() {
    const data = {};
    for (const el of form.elements) {
      if (!el.name || el.name === "csrfmiddlewaretoken") continue;
      if (el.type === "checkbox") data[el.name] = el.checked;
      else if (NUMBER_FIELDS.includes(el.name) && el.value !== "") data[el.name] = Number(el.value);
      else data[el.name] = el.value;
    }
    return data;
  }

  function errorSlot(field) {
    return form.querySelector(`[data-error-for="${field}"]`);
  }

  function setFieldError(field, messages) {
    const slot = errorSlot(field) || errorSlot("non_field_errors");
    slot.textContent = [].concat(messages).join(" ");
    const input = form.elements[field];
    if (input && input.setAttribute) input.setAttribute("aria-invalid", messages.length ? "true" : "false");
  }

  function clearErrors() {
    form.querySelectorAll("[data-error-for]").forEach((el) => (el.textContent = ""));
    form.querySelectorAll('[aria-invalid="true"]').forEach((el) => el.setAttribute("aria-invalid", "false"));
  }

  function showErrors(errors) {
    for (const [field, messages] of Object.entries(errors)) setFieldError(field, messages);
    const first = form.querySelector('[aria-invalid="true"]') || form.querySelector("[data-error-for]:not(:empty)");
    if (!first) return;
    first.scrollIntoView({ block: "center" });
    if (first.focus) first.focus({ preventScroll: true });
  }

  function parseDate(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  }

  function toIso(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function formatDate(iso) {
    const date = parseDate(iso);
    const weekday = "일월화수목금토"[date.getDay()];
    return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일(${weekday})`;
  }

  // 연락 가능 날짜는 수업 희망일 전날까지만 고를 수 있다.
  preferredInput.addEventListener("change", () => {
    if (!preferredInput.value) {
      contactInput.removeAttribute("max");
      return;
    }
    const dayBefore = parseDate(preferredInput.value);
    dayBefore.setDate(dayBefore.getDate() - 1);
    contactInput.max = toIso(dayBefore);
  });

  contactInput.addEventListener("change", () => {
    if (!contactInput.value) return setFieldError("contact_date", []);
    const day = parseDate(contactInput.value).getDay();
    if (day === 0 || day === 6) {
      setFieldError("contact_date", [`${formatDate(contactInput.value)}은 주말입니다. 평일(월~금)을 골라 주세요.`]);
    } else {
      setFieldError("contact_date", []);
    }
  });

  function setBusy(busy) {
    submitting = busy;
    submitButton.disabled = busy;
    form.setAttribute("aria-busy", busy ? "true" : "false");
    submitLabel.textContent = busy ? submitLabel.dataset.busyLabel : submitLabel.dataset.idleLabel;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submitting) return;
    clearErrors();
    setBusy(true);
    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": form.elements.csrfmiddlewaretoken.value,
        },
        credentials: "same-origin",
        body: JSON.stringify(payload()),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 201) {
        done.querySelector("[data-contact-date]").textContent = formatDate(body.contact_date);
        form.hidden = true;
        done.hidden = false;
        done.scrollIntoView({ block: "center" });
        done.querySelector("h3").focus({ preventScroll: true });
      } else if (response.status === 400) {
        showErrors(body);
      } else if (response.status === 429) {
        showErrors({ non_field_errors: ["제출이 잠시 너무 많았습니다. 조금 뒤에 다시 제출해 주세요."] });
      } else {
        showErrors({ non_field_errors: ["접수 중 문제가 생겼습니다. 잠시 후 다시 제출해 주세요."] });
      }
    } catch (error) {
      showErrors({ non_field_errors: ["서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 다시 제출해 주세요."] });
    } finally {
      setBusy(false);
    }
  });
})();
