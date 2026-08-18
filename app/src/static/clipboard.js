async function copyTextCompat(text, button) {
  let copied = false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      copied = true;
    }
  } catch (_) {}

  if (!copied) {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.left = '-9999px';
    area.style.top = '0';
    document.body.appendChild(area);
    area.focus();
    area.select();
    area.setSelectionRange(0, area.value.length);
    try {
      copied = document.execCommand('copy');
    } catch (_) {
      copied = false;
    }
    document.body.removeChild(area);
  }

  if (button) {
    const original = button.textContent;
    button.textContent = copied ? 'Скопировано' : 'Не удалось скопировать';
    setTimeout(() => { button.textContent = original; }, 1600);
  }
  return copied;
}

async function copyAnalysis() {
  if (!currentResult) return;
  await copyTextCompat(textAnalysis(currentResult.result), document.activeElement);
}

async function copyPrompt() {
  if (!currentResult) return;
  await copyTextCompat(currentResult.result.reproduction_prompt, document.activeElement);
}
