// 신청 폼: POST /api/applications/를 호출하고 필드별 오류와 접수 완료 메시지를 보여준다.
(function () {
  const form = document.getElementById("apply-form");
  if (!form) return;
  const done = document.getElementById("apply-done");
  const submitButton = form.querySelector('button[type="submit"]');
  const NUMBER_FIELDS = ["class_count", "session_count"];

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

  function clearErrors() {
    form.querySelectorAll("[data-error-for]").forEach((el) => (el.textContent = ""));
  }

  function showErrors(errors) {
    let shown = false;
    for (const [field, messages] of Object.entries(errors)) {
      const slot =
        form.querySelector(`[data-error-for="${field}"]`) ||
        form.querySelector('[data-error-for="non_field_errors"]');
      slot.textContent = [].concat(messages).join(" ");
      shown = true;
    }
    if (shown) form.querySelector("[data-error-for]:not(:empty)")?.scrollIntoView({ block: "center" });
  }

  function formatDate(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const weekday = "일월화수목금토"[new Date(y, m - 1, d).getDay()];
    return `${y}년 ${m}월 ${d}일(${weekday})`;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();
    submitButton.disabled = true;
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
      } else if (response.status === 400) {
        showErrors(body);
      } else if (response.status === 429) {
        showErrors({ non_field_errors: ["요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."] });
      } else {
        showErrors({ non_field_errors: ["접수 중 문제가 생겼습니다. 잠시 후 다시 시도해 주세요."] });
      }
    } catch (error) {
      showErrors({ non_field_errors: ["네트워크 연결을 확인해 주세요."] });
    } finally {
      submitButton.disabled = false;
    }
  });
})();
