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
    area.setAttribute('aria-hidden', 'true');
    area.style.position = 'fixed';
    area.style.top = '0';
    area.style.left = '0';
    area.style.width = '1px';
    area.style.height = '1px';
    area.style.opacity = '0';
    area.style.pointerEvents = 'none';
    document.body.appendChild(area);

    try {
      area.focus({preventScroll: true});
      area.select();
      area.setSelectionRange(0, area.value.length);
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

  if (!copied) {
    window.prompt('Скопируйте текст вручную:', text);
  }

  return copied;
}

async function copyAnalysis(event) {
  event?.preventDefault();
  event?.stopPropagation();
  if (!currentResult) return;
  await copyTextCompat(textAnalysis(currentResult.result), event?.currentTarget || null);
}

async function copyPrompt(event) {
  event?.preventDefault();
  event?.stopPropagation();
  if (!currentResult) return;
  await copyTextCompat(currentResult.result.reproduction_prompt, event?.currentTarget || null);
}
