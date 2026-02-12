$(document).ready(function() {
    let dataset = [];
    let currentIndex = 0;
    let currentMode = 'default_natural';
    const viewerContainer = $('#dataset-viewer');

    if (viewerContainer.length === 0) return;

    // Fetch data
    const p1 = $.getJSON('./static/inconsistencies/annotations_2024.json').then(data => {
        const items = [];
        Object.values(data).forEach(group => {
            group.forEach(item => {
                item._year = '2024';
                items.push(item);
            });
        });
        return items;
    });

    const p2 = $.getJSON('./static/inconsistencies/annotations_2025.json').then(data => {
        const items = [];
        Object.values(data).forEach(group => {
            group.forEach(item => {
                item._year = '2025';
                items.push(item);
            });
        });
        return items;
    });

    Promise.all([p1, p2]).then(results => {
        dataset = [...results[0], ...results[1]];
        renderViewer();
    }).catch(function() {
        $('#viewer-content-body').html('<div class="notification is-danger">Failed to load dataset annotations.</div>');
    });

    // Event Listeners
    $('.viewer-tab').click(function() {
        $('.viewer-tab').removeClass('is-active');
        $(this).addClass('is-active');
        currentMode = $(this).data('mode');
        renderViewer();
    });

    $('#prev-btn').click(function() {
        if (currentIndex > 0) {
            currentIndex--;
            renderViewer();
        }
    });

    $('#next-btn').click(function() {
        if (currentIndex < dataset.length - 1) {
            currentIndex++;
            renderViewer();
        }
    });

    $('#page-input').on('change', function() {
        let val = parseInt($(this).val());
        if (!isNaN(val) && val >= 1 && val <= dataset.length) {
            currentIndex = val - 1;
            renderViewer();
        } else {
            // Reset to current valid index if invalid
            $(this).val(currentIndex + 1);
        }
    });

    function renderViewer() {
        if (dataset.length === 0) return;
        const item = dataset[currentIndex];
        
        // Update Page Input and Total
        $('#page-input').val(currentIndex + 1);
        $('#total-pages').text(`/ ${dataset.length}`);
        
        // Disable/Enable buttons
        $('#prev-btn').attr('disabled', currentIndex === 0);
        $('#next-btn').attr('disabled', currentIndex === dataset.length - 1);

        // Get MCQ data for mode
        let mcqData = item.mcq[currentMode];
        // Fallback if specific mode is missing (though it shouldn't be based on requirements)
        if (!mcqData) {
            mcqData = item.mcq['default_natural']; 
        }

        const contentDiv = $('#viewer-content-body');
        contentDiv.empty();
        
        if (!mcqData) {
            contentDiv.html('<p>No data available for this mode.</p>');
            return;
        }

        // 1. Question
        contentDiv.append(`<h4 class="title is-5 mb-2">Question</h4>`);
        contentDiv.append(`<div class="content mb-4"><p>${mcqData.question}</p></div>`);

        // 2. Inconsistency Parts
        contentDiv.append(`<h4 class="title is-5 mb-2">Context</h4>`);
        const partsContainer = $('<div class="columns is-multiline mb-4"></div>');
        
        if (item.inconsistency_parts && item.inconsistency_parts.length > 0) {
            item.inconsistency_parts.forEach(part => {
                const col = $('<div class="column is-full"></div>');
                if (part.type === 'image') {
                    const imgPath = `./static/inconsistencies/images_${item._year}/${part.image_id}.png`;
                    col.append(`
                        <figure class="image">
                            <img src="${imgPath}" alt="Inconsistency Image" style="width: 100%; height: auto; object-fit: contain;">
                            <figcaption class="is-size-7 has-text-grey">Page ${part.page}</figcaption>
                        </figure>
                    `);
                } else if (part.type === 'text') {
                    col.append(`
                        <div class="notification is-light">
                            <span class="tag is-info is-light mb-1">Page ${part.page}</span>
                            <p class="is-family-secondary">"${part.content}"</p>
                        </div>
                    `);
                }
                partsContainer.append(col);
            });
        } else {
            partsContainer.append('<div class="column"><p class="has-text-grey-light">No context parts available.</p></div>');
        }
        contentDiv.append(partsContainer);

        // 3. Answers
        contentDiv.append(`<h4 class="title is-5 mb-2">Answer Options</h4>`);
        
        const answers = [];
        // Correct
        if (mcqData.letters && mcqData.letters.length > 0) {
            answers.push({
                letter: mcqData.letters[0],
                text: mcqData.correct,
                isCorrect: true
            });
            
            // Incorrect
            if (mcqData.incorrect) {
                mcqData.incorrect.forEach((text, idx) => {
                    // letters[0] is correct, so incorrect start at 1
                    if (idx + 1 < mcqData.letters.length) {
                        answers.push({
                            letter: mcqData.letters[idx + 1],
                            text: text,
                            isCorrect: false
                        });
                    }
                });
            }

            // Sort by letter A, B, C, D
            answers.sort((a, b) => a.letter.localeCompare(b.letter));

            const isJsonMode = (currentMode === 'default' || currentMode === 'edit');
            const answersContainer = $('<div class="columns is-multiline"></div>');
            
            answers.forEach(ans => {
                let displayValid = ans.text;
                // Try to pretty print JSON if needed
                if (isJsonMode && typeof ans.text === 'string' && ans.text.trim().startsWith('{')) {
                    try {
                        const parsed = JSON.parse(ans.text);
                        displayValid = `<pre class="is-size-7" style="background-color: transparent; padding: 0; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(parsed, null, 2)}</pre>`;
                    } catch(e) {
                        // keep original if parse fails
                    }
                }
                
                const styleClass = ans.isCorrect ? 'has-background-success-light' : '';
                const icon = ans.isCorrect ? '<span class="icon has-text-success is-pulled-right"><i class="fas fa-check"></i></span>' : '';
                const colClass = isJsonMode ? 'is-6' : 'is-12';

                const itemHtml = `
                    <div class="column ${colClass}">
                        <div class="box ${styleClass} p-3" style="height: 100%;">
                            <div class="columns is-mobile is-vcentered">
                                <div class="column is-narrow">
                                    <span class="tag is-dark is-medium is-rounded">${ans.letter}</span>
                                </div>
                                <div class="column">
                                    ${displayValid}
                                </div>
                                <div class="column is-narrow">
                                    ${icon}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                answersContainer.append(itemHtml);
            });
            contentDiv.append(answersContainer);
        }
    }
});
