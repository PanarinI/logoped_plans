// app/tooltip.js
function initProCheckboxTooltip() {
    const checkboxLabel = document.querySelector('#pro-checkbox .wrap .label-wrap');
    if (checkboxLabel) {
        checkboxLabel.setAttribute(
            'data-tooltip',
            'Включает упражнения из: Logopedia.pro, Maam.ru и других проверенных источников'
        );

        if (!checkboxLabel.querySelector('.tooltip-icon')) {
            const icon = document.createElement('span');
            icon.className = 'tooltip-icon';
            icon.textContent = ' ⓘ';
            icon.style.color = '#1976D2';
            checkboxLabel.querySelector('label').appendChild(icon);
        }
    }
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', initProCheckboxTooltip);

// Отслеживание динамических изменений DOM
new MutationObserver(initProCheckboxTooltip).observe(document.body, {
    childList: true,
    subtree: true
});