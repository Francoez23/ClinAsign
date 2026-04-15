document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 3500);
    });

    const passwordToggles = document.querySelectorAll('[data-password-toggle]');
    passwordToggles.forEach((toggle) => {
        const targetId = toggle.getAttribute('data-target');
        const passwordInput = targetId ? document.getElementById(targetId) : null;
        if (!passwordInput) {
            return;
        }

        const toggleLabel = toggle.querySelector('[data-password-toggle-label]');
        const hiddenIcon = toggle.querySelector('[data-icon-hidden]');
        const visibleIcon = toggle.querySelector('[data-icon-visible]');

        const setPasswordVisibility = (isVisible) => {
            passwordInput.type = isVisible ? 'text' : 'password';
            toggle.dataset.state = isVisible ? 'visible' : 'hidden';
            toggle.setAttribute('aria-label', isVisible ? 'Hide password' : 'Show password');
            toggle.setAttribute('aria-pressed', isVisible ? 'true' : 'false');

            if (toggleLabel) {
                toggleLabel.textContent = isVisible ? 'Hide' : 'Show';
            }
            if (hiddenIcon) {
                hiddenIcon.hidden = isVisible;
            }
            if (visibleIcon) {
                visibleIcon.hidden = !isVisible;
            }
        };

        setPasswordVisibility(passwordInput.type === 'text');
        toggle.addEventListener('click', function () {
            setPasswordVisibility(passwordInput.type === 'password');
        });
    });

    const plainTextInputs = document.querySelectorAll('[data-plain-text-input]');
    plainTextInputs.forEach((input) => {
        const unlockInput = () => {
            if (input.readOnly) {
                input.readOnly = false;
            }
        };

        input.addEventListener('focus', unlockInput, { once: true });
    });

    const lockoutForms = document.querySelectorAll('[data-login-lockout-seconds]');
    lockoutForms.forEach((form) => {
        let secondsRemaining = Number(form.getAttribute('data-login-lockout-seconds'));
        if (!secondsRemaining || secondsRemaining < 1) {
            return;
        }

        const controls = form.querySelectorAll('input:not([type="hidden"]), button');
        const submitButton = form.querySelector('.login-submit');
        const defaultLabel = submitButton?.dataset.defaultLabel || submitButton?.textContent || 'Sign In';

        const setControlsDisabled = (isDisabled) => {
            controls.forEach((control) => {
                control.disabled = isDisabled;
            });
        };

        const tick = () => {
            setControlsDisabled(secondsRemaining > 0);

            if (submitButton) {
                submitButton.textContent = secondsRemaining > 0
                    ? `Try again in ${secondsRemaining}s`
                    : defaultLabel;
            }

            if (secondsRemaining <= 0) {
                form.removeAttribute('data-login-lockout-seconds');
                return;
            }

            secondsRemaining -= 1;
            window.setTimeout(tick, 1000);
        };

        tick();
    });
});
