export const formatDate = (dateStr, monthVal, yearVal) => {
    if (dateStr) {
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (e) {
            console.warn("Invalid date string:", dateStr);
            return dateStr;
        }
    }

    if (yearVal) {
        const months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];

        let monthName = "";

        if (monthVal) {
            // Handle if monthVal is number or string representation of number
            if (!isNaN(monthVal) && parseInt(monthVal) >= 1 && parseInt(monthVal) <= 12) {
                monthName = months[parseInt(monthVal) - 1];
            } else if (typeof monthVal === 'string' && months.includes(monthVal)) {
                // If it's already a full month name
                monthName = monthVal;
            } else {
                // Fallback or short name handling could go here if needed
                monthName = monthVal;
            }
        }

        return monthName ? `${monthName} ${yearVal}` : `${yearVal}`;
    }

    return '';
};
