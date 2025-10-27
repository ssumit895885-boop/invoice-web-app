// Wait for the DOM to be fully loaded before running any script
document.addEventListener("DOMContentLoaded", function() {

    // Find the invoice form by its ID
    const invoiceForm = document.getElementById("invoice-form");

    // Only run this code if we are on a page that *has* the invoice form
    if (invoiceForm) {
        
        // --- 1. Get All Our Elements ---
        const itemsContainer = document.getElementById("items-container");
        const addItemButton = document.getElementById("add-item");
        
        // Summary fields
        const summarySubtotal = document.getElementById("summary-subtotal");
        const summaryGst = document.getElementById("summary-gst");
        const summaryTotal = document.getElementById("summary-total");

        // --- 2. The Main Calculation Function ---
        // This function will run every time something changes
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
            });

            // Calculate the final grand total
            const grandTotal = subtotal + totalGst;

            // Get the currency symbol from the profile (we'll add this later)
            // For now, let's just format the numbers.
            
            // Update the summary box in the UI
            summarySubtotal.textContent = subtotal.toFixed(2);
            summaryGst.textContent = totalGst.toFixed(2);
            summaryTotal.textContent = grandTotal.toFixed(2);
        }

        // --- 3. "Add Item" Button Logic ---
        addItemButton.addEventListener("click", function() {
            // Find the first row to use as a template
            const templateRow = itemsContainer.querySelector(".item-row");
            
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
                }
            });
            // Reset the select to 18% (or any default)
            newRow.querySelector('select[name="tax_percent"]').value = "18";
            // Reset the line total span
            newRow.querySelector('.line-total').textContent = "0.00";
            
            // Add the new row to the container
            itemsContainer.appendChild(newRow);
        });

        // --- 4. "Remove Item" & Calculation Logic (Event Delegation) ---
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
            // If the user types in *any* input (qty, rate, or tax)
            if (event.target.tagName === "INPUT" || event.target.tagName === "SELECT") {
                // Recalculate everything
                calculateTotals();
            }
        });

        // --- 5. Initial Calculation ---
        // Run the calculation once when the page loads
        calculateTotals();
    }
});