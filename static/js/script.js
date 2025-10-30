// Wait for the DOM to be fully loaded before running any script
document.addEventListener("DOMContentLoaded", function() {

    // --- 1. INVOICE FORM SCRIPT ---
    // Find the invoice form by its ID
    const invoiceForm = document.getElementById("invoice-form");

    // Only run this code if we are on a page that *has* the invoice form
    if (invoiceForm) {
        
        // --- Get All Our Elements ---
        const itemsContainer = document.getElementById("items-container");
        const addItemButton = document.getElementById("add-item");
        const summarySubtotal = document.getElementById("summary-subtotal");
        const summaryGst = document.getElementById("summary-gst");
        const summaryTotal = document.getElementById("summary-total");

        // Safety check: Don't run if core elements are missing
        if (!itemsContainer || !addItemButton || !summarySubtotal || !summaryGst || !summaryTotal) {
            console.warn("Invoice script stopped: Not all form elements were found.");
        } else {

            // --- The Main Calculation Function ---
            function calculateTotals() {
                let subtotal = 0;
                let totalGst = 0;

                // Find ALL item rows in the container
                const itemRows = itemsContainer.querySelectorAll(".item-row");

                itemRows.forEach(row => {
                    // Find the inputs *within* the current row
                    const qtyInput = row.querySelector('input[name="qty"]');
                    const rateInput = row.querySelector('input[name="rate"]');
                    const taxSelect = row.querySelector('select[name="tax_percent"]');
                    const lineTotalSpan = row.querySelector(".line-total");

                    // Safety check for row elements
                    if (qtyInput && rateInput && taxSelect && lineTotalSpan) {
                        // Get the values, using 0 as a default if empty or invalid
                        const qty = parseFloat(qtyInput.value) || 0;
                        const rate = parseFloat(rateInput.value) || 0;
                        const taxPercent = parseFloat(taxSelect.value) || 0;

                        // Calculate line totals
                        const lineSubtotal = qty * rate;
                        const lineGst = lineSubtotal * (taxPercent / 100.0);
                        const lineTotal = lineSubtotal + lineGst;

                        // Update the UI for *this row*
                        lineTotalSpan.textContent = lineTotal.toFixed(2);
                        
                        // Add to the grand totals
                        subtotal += lineSubtotal;
                        totalGst += lineGst;
                    }
                });

                // Calculate the final grand total
                const grandTotal = subtotal + totalGst;
                
                // Update the summary box in the UI
                summarySubtotal.textContent = subtotal.toFixed(2);
                summaryGst.textContent = totalGst.toFixed(2);
                summaryTotal.textContent = grandTotal.toFixed(2);
            }

            // --- "Add Item" Button Logic ---
            addItemButton.addEventListener("click", function() {
                // Find the first row to use as a template
                const templateRow = itemsContainer.querySelector(".item-row");
                
                if (!templateRow) return; // Safety check
                
                // Clone it (deep clone)
                const newRow = templateRow.cloneNode(true);
                
                // Clear all input values in the *new* row
                newRow.querySelectorAll("input").forEach(input => {
                    if(input.type === "number") {
                        input.value = "0"; // Default numbers to 0
                    } else if(input.name === "qty") {
                        input.value = "1"; // Default qty to 1
                    } 
                    else {
                        input.value = ""; // Clear text inputs
    M             }
                });
                // Reset the select to 18% (or any default)
                newRow.querySelector('select[name="tax_percent"]').value = "18";
                // Reset the line total span
                newRow.querySelector('.line-total').textContent = "0.00";
    A         
                // Add the new row to the container
                itemsContainer.appendChild(newRow);
            });

            // --- "Remove Item" & Calculation Logic (Event Delegation) ---
            // We listen for clicks/inputs on the *entire container*
            itemsContainer.addEventListener("click", function(event) {
                // Check if the clicked element was a "Remove" button
                if (event.target.classList.contains("btn-remove")) {
                    
                    // Safety check: Don't remove the *last* item row
                    if (itemsContainer.querySelectorAll(".item-row").length > 1) {
                        // Find the parent .item-row and remove it
                        event.target.closest(".item-row").remove();
                        // After removing, recalculate everything
                        calculateTotals();
                    } else {
                        alert("You must have at least one item.");
                    }
                }
            });

            itemsContainer.addEventListener("input", function(event) {
    img           // If the user types in *any* input (qty, rate, or tax)
                if (event.target.tagName === "INPUT" || event.target.tagName === "SELECT") {
                    // Recalculate everything
                    calculateTotals();
                }
            });

            // --- Initial Calculation ---
    g       // Run the calculation once when the page loads
            calculateTotals();
        }
    } // --- END of if(invoiceForm) block ---


    // --- 2. PASSWORD TOGGLE SCRIPT (REVERTED TO CLICK) ---
    const togglePassword = document.getElementById('toggle-password');
    const passwordInput = document.getElementById('password');

    // Only run this code if we are on a page that *has* the toggle button
    if (togglePassword && passwordInput) {
        
        togglePassword.addEventListener('click', function() {
            // Check the current type of the input
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Change the "Show" / "Hide" text
            if (type === 'password') {
                this.textContent = 'Show';
            } else {
                this.textContent = 'Hide';
            }
        });
    }
    // --- END NEW SCRIPT ---

}); // --- END of DOMContentLoaded listener ---