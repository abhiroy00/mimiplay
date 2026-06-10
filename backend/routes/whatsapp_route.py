from flask import Blueprint, jsonify, request
from routes.auth_routes import token_required
from datetime import datetime
from extensions import db
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)
whatsapp_bp = Blueprint("whatsapp", __name__)


# ================================
# WHATSAPP MANAGEMENT ENDPOINTS
# ================================
@whatsapp_bp.route("/api/whatsapp/delivery-stats", methods=["GET"])
@token_required
def get_delivery_stats():
    """Get WhatsApp delivery statistics"""
    try:
        # Get stats from whatsapp_logs collection
        total_sent = db["whatsapp_logs"].count_documents({})
        delivered = db["whatsapp_logs"].count_documents({"status": "delivered"})
        failed = db["whatsapp_logs"].count_documents({"status": "failed"})
        pending = db["whatsapp_logs"].count_documents({"status": "pending"})
        
        success_rate = round((delivered / total_sent * 100), 1) if total_sent > 0 else 0
        
        return jsonify({
            "status": "success",
            "stats": {
                "totalSent": total_sent,
                "delivered": delivered,
                "failed": failed,
                "pending": pending,
                "successRate": success_rate
            }
        })
    except Exception as e:
        logger.error("[delivery-stats] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@whatsapp_bp.route("/api/whatsapp/recent-messages", methods=["GET"])
@token_required
def get_recent_messages():
    """Get recent WhatsApp messages with delivery status"""
    try:
        limit = int(request.args.get('limit', 50))
        
        messages = list(db["whatsapp_logs"].find({}).sort("sent_at", -1).limit(limit))
        
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "recipient_name": msg.get("recipient_name", "Unknown"),
                "phone_number": msg.get("phone_number", "N/A"),
                "message_type": msg.get("message_type", "unknown"),
                "status": msg.get("status", "pending"),
                "sent_at": msg.get("sent_at", ""),
                "message_preview": msg.get("message_content", "")[:100] + "..." if len(msg.get("message_content", "")) > 100 else msg.get("message_content", "")
            })
        
        return jsonify({
            "status": "success",
            "messages": formatted_messages
        })
    except Exception as e:
        logger.error("[recent-messages] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@whatsapp_bp.route("/api/whatsapp/templates", methods=["GET"])
@token_required
def get_message_templates():
    """Get WhatsApp message templates"""
    try:
        templates = list(db["whatsapp_templates"].find({}))
        
        formatted_templates = []
        for template in templates:
            formatted_templates.append({
                "id": str(template["_id"]),
                "name": template.get("name", ""),
                "type": template.get("type", ""),
                "content": template.get("content", ""),
                "variables": template.get("variables", []),
                "created_at": template.get("created_at", "")
            })
        
        return jsonify({
            "status": "success",
            "templates": formatted_templates
        })
    except Exception as e:
        logger.error("[get-templates] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@whatsapp_bp.route("/api/whatsapp/templates", methods=["POST"])
@token_required
def save_message_template():
    """Save or update WhatsApp message template"""
    try:
        data = request.get_json() or {}
        
        template_data = {
            "name": data.get("name", ""),
            "type": data.get("type", "custom"),
            "content": data.get("content", ""),
            "variables": data.get("variables", []),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if data.get("id"):
            # Update existing template
            db["whatsapp_templates"].update_one(
                {"_id": ObjectId(data["id"])},
                {"$set": template_data}
            )
        else:
            # Create new template
            template_data["created_at"] = datetime.utcnow().isoformat()
            db["whatsapp_templates"].insert_one(template_data)
        
        return jsonify({"status": "success", "msg": "Template saved successfully"})
    except Exception as e:
        logger.error("[save-template] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@whatsapp_bp.route("/api/whatsapp/templates/<template_id>", methods=["DELETE"])
@token_required
def delete_message_template(template_id):
    """Delete WhatsApp message template"""
    try:
        result = db["whatsapp_templates"].delete_one({"_id": ObjectId(template_id)})
        
        if result.deleted_count == 0:
            return jsonify({"status": "error", "msg": "Template not found"}), 404
        
        return jsonify({"status": "success", "msg": "Template deleted successfully"})
    except Exception as e:
        logger.error("[delete-template] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@whatsapp_bp.route("/api/whatsapp/export-delivery-report", methods=["GET"])
@token_required
def export_delivery_report():
    """Export WhatsApp delivery report"""
    try:
        format_type = request.args.get('format', 'csv').lower()
        
        # Get delivery data
        messages = list(db["whatsapp_logs"].find({}).sort("sent_at", -1))
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow(['Date', 'Recipient', 'Phone', 'Message Type', 'Status', 'Content Preview'])
            
            # Data
            for msg in messages:
                writer.writerow([
                    msg.get('sent_at', ''),
                    msg.get('recipient_name', ''),
                    msg.get('phone_number', ''),
                    msg.get('message_type', ''),
                    msg.get('status', ''),
                    msg.get('message_content', '')[:100]
                ])
            
            output.seek(0)
            
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={"Content-disposition": "attachment; filename=whatsapp-delivery-report.csv"}
            )
        
        else:
            return jsonify({"status": "error", "msg": "Unsupported format"}), 400
            
    except Exception as e:
        logger.error("[export-delivery-report] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@whatsapp_bp.route("/api/whatsapp/test-purchased-number", methods=["POST"])
@token_required
def test_purchased_number():
    """Test the purchased WhatsApp number by sending a test message"""
    try:
        data = request.get_json() or {}
        test_to = data.get("to")  # e.g. "+919601930581"
        
        if not test_to:
            return jsonify({"status": "error", "msg": "Provide 'to' phone number in body"}), 400
        
        from services.whatsapp_service import send_whatsapp
        result = send_whatsapp(
            number=test_to,
            message="✅ Test from Mimi! Your purchased Twilio number (+12055309988) is working correctly.",
            message_type="test",
            recipient_name="Test Recipient"
        )
        
        return jsonify({
            "status": "success" if result else "failed",
            "sent": result,
            "from_number": "+12055309988"
        })
    except Exception as e:
        logger.error("[test-purchased-number] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@whatsapp_bp.route("/api/whatsapp/send-activity-result", methods=["POST"])
@token_required
def manual_send_activity_result():
    """Manually send activity result to parent via WhatsApp"""
    try:
        data = request.get_json() or {}
        student_name = data.get("student_name", "")
        activity_name = data.get("activity_name", "")
        stars = data.get("stars", 0)
        score = data.get("score", 0)
        
        if not student_name or not activity_name:
            return jsonify({"status": "error", "msg": "student_name and activity_name required"}), 400
        
        from services.whatsapp_service import send_activity_result_to_parent
        result = send_activity_result_to_parent(student_name, activity_name, stars, score)
        
        return jsonify({
            "status": "success" if result else "failed",
            "sent": result,
            "student": student_name
        })
    except Exception as e:
        logger.error("[manual-activity-result] ERROR: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500